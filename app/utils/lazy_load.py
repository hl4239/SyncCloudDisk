# example_lazy_pydantic_with_helper.py
from __future__ import annotations
import asyncio
import time
import inspect
from copy import deepcopy
from typing import (
    Any, Awaitable, Callable, Generic, Optional, TypeVar, Union, overload, List
)

from app.utils.cache import async_ttl_cache

T = TypeVar("T")
U = TypeVar("U")
Provider = Union[Callable[[], Union[T, Awaitable[T]]], Awaitable[T], T]


# ---------------- Lazy implementation with optional caching ----------------
class Lazy(Generic[T]):
    """
    Lazy wrapper with optional caching.

    ttl semantics:
      - None  -> permanent cache (default): once provider produced a result, it is kept forever
      - > 0.0 -> time-limited cache in seconds (expires after ttl seconds)
      - 0.0   -> no cache (always call provider on await)

    Usage notes:
      - Pass a callable or awaitable/value to Lazy. Internally we support:
          * provider is an awaitable (coroutine object) -> it will be awaited directly
          * provider is a callable -> it will be called; if the call returns awaitable, that will be awaited
          * provider is a plain value -> returned directly
      - map(fn) / attr(name) / __getattr__ return Lazy objects (they pass a callable provider, not a coroutine).
      - __getitem__ now returns Lazy as well, consistent with attr/map behavior.
    """
    __slots__ = ("_provider", "_running_task", "_ttl", "_cached_result", "_cache_time")

    def __init__(self, provider: Provider[T], ttl: Optional[float] = None):
        # 默认永久缓存（ttl=None）
        self._provider = provider
        self._running_task: Optional[asyncio.Task] = None
        self._ttl = ttl  # None = permanent cache, 0.0 = no cache, >0 = TTL seconds
        self._cached_result: Optional[T] = None
        self._cache_time: Optional[float] = None

    @classmethod
    def wrap(cls, provider: Provider[T], ttl: Optional[float] = None) -> "Lazy[T]":
        if isinstance(provider, Lazy):
            return provider if ttl is None else cls(provider._provider, ttl)
        return cls(provider, ttl)

    def _is_cache_valid(self) -> bool:
        # 如果没有缓存过结果一定无效
        if self._cached_result is None or self._cache_time is None:
            return False
        # 明确禁止缓存
        if self._ttl == 0:
            return False
        # 永久缓存
        if self._ttl is None:
            return True
        # 有限 ttl
        return time.time() - self._cache_time < self._ttl

    async def _call_provider(self) -> T:
        prov = self._provider
        # provider 本身是 awaitable（coroutine object）
        if inspect.isawaitable(prov):
            return await prov  # type: ignore
        # provider 是 callable（可能是 async def function 或普通 function）
        if callable(prov):
            maybe = prov()
            if inspect.isawaitable(maybe):
                return await maybe  # type: ignore
            return maybe  # type: ignore
        # provider 是值
        return prov  # type: ignore

    async def _ensure_run(self) -> T:
        # 先检查缓存
        if self._is_cache_valid():
            return self._cached_result  # type: ignore

        # 若已有正在运行的任务，复用它（in-flight dedupe）
        if self._running_task is not None:
            return await self._running_task

        # 启动新任务
        loop = asyncio.get_running_loop()
        task = loop.create_task(self._call_provider())
        self._running_task = task

        try:
            res = await task
            # 除非 ttl == 0（表示不缓存），否则保存结果（ttl=None -> 永久）
            if self._ttl != 0:
                self._cached_result = res
                self._cache_time = time.time()
            return res
        finally:
            # 清理运行中的任务引用
            self._running_task = None

    def __await__(self):
        return self._ensure_run().__await__()

    def __repr__(self) -> str:
        return f"Lazy(provider={self._provider!r}, ttl={self._ttl})"

    # 使 __getitem__ 返回 Lazy（而不是 coroutine），语义与 attr 一致
    def __getitem__(self, idx) -> "Lazy[Any]":
        async def _provider():
            val = await self._ensure_run()
            return val[idx]
        # 注意：传入可调用 async function（不要调用它）
        return Lazy(_provider, self._ttl)

    # ---------------- 新增：map / attr / __getattr__ ----------------
    def map(self, fn: Callable[[T], Union[U, Awaitable[U], "Lazy[U]"]], *, ttl: Optional[float] = None) -> "Lazy[U]":
        """
        对延迟值应用一个转换函数，返回新的 Lazy[U]。
        fn 可以返回普通值 / awaitable / Lazy。
        """
        async def _provider():
            v = await self._ensure_run()
            res = fn(v)
            if isinstance(res, Lazy):
                return await res  # type: ignore
            if inspect.isawaitable(res):
                return await res  # type: ignore
            return res  # type: ignore

        return Lazy(_provider, ttl if ttl is not None else self._ttl)

    def attr(self, name: str, *, ttl: Optional[float] = None) -> "Lazy[Any]":
        """
        延迟读取属性 name，并自动 unwrap 属性值（如果属性本身是 Lazy 或 awaitable）。
        返回 Lazy（需要 await 才会执行 provider）。
        """
        async def _provider():
            v = await self._ensure_run()
            a = getattr(v, name)
            if isinstance(a, Lazy):
                return await a
            if inspect.isawaitable(a):
                return await a
            return a

        return Lazy(_provider, ttl if ttl is not None else self._ttl)

    def __getattr__(self, name: str):
        # 不拦截内部属性
        if name.startswith("_"):
            raise AttributeError(name)
        return self.attr(name)

    # ---------------- 运行时：pydantic v1 validator hook ----------------
    @classmethod
    def _wrap_input(cls, v: Any, ttl: Optional[float] = None):
        if isinstance(v, Lazy):
            return v
        if inspect.isawaitable(v):
            return Lazy(v, ttl)
        if callable(v):
            return Lazy(v, ttl)
        return Lazy(lambda: v, ttl)

    @classmethod
    def __get_validators__(cls):
        yield cls._validate_pydantic_v1

    @classmethod
    def _validate_pydantic_v1(cls, v, field=None):
        return cls._wrap_input(v)

    # pydantic v2 hook（如果可用）
    try:
        from pydantic import core_schema  # type: ignore

        @classmethod
        def __get_pydantic_core_schema__(cls, source_type, handler=None):
            return core_schema.no_info_plain_validator(cls._validate_pydantic_v2)

        @classmethod
        def _validate_pydantic_v2(cls, v, info=None):
            return cls._wrap_input(v)
    except Exception:
        pass


# ---------------- Editor-friendly helper with overloads ----------------
@overload
def lazy(provider: Callable[[], Awaitable[T]], *, ttl: Optional[float] = None) -> Lazy[T]: ...
@overload
def lazy(provider: Callable[[], T], *, ttl: Optional[float] = None) -> Lazy[T]: ...
@overload
def lazy(awaitable: Awaitable[T], *, ttl: Optional[float] = None) -> Lazy[T]: ...
@overload
def lazy(value: T, *, ttl: Optional[float] = None) -> Lazy[T]: ...


def lazy(provider: Provider[T], *, ttl: Optional[float] = None) -> Lazy[T]:
    """
    helper: 推荐在代码里用 lazy(lambda: ...) 明确表示这是 Lazy[T]。
    默认 ttl=None 表示永久缓存。传 ttl=0 表示不缓存（让 provider 自身负责缓存）。
    """
    return Lazy.wrap(provider, ttl)


# ---------------- Example async provider (with ttl cache) ----------------
async def get_description(title: str) -> str:
    print(f"[provider] get_description({title}) running")
    await asyncio.sleep(0.15)
    return f"Description for {title}"


# ---------------- pydantic model (works with v1 and v2) ----------------
try:
    import pydantic as _pyd
    from pydantic import BaseModel

    PYDANTIC = True
except Exception:
    PYDANTIC = False
    BaseModel = object

if not PYDANTIC:
    raise RuntimeError("Please install pydantic (v1 or v2) to run this example.")


class Movie(BaseModel):
    title: str
    description: Optional[Lazy[str]] = None
    descriptions: Optional[List[Lazy[str]]] = None


class ExampleM(BaseModel):
    title: str
    title1: str


async def get_m():
    print("[provider] get_m() running")
    await asyncio.sleep(3)
    return ExampleM(title="good", title1="zxc")


# ---------------- Demo main ----------------
async def main():
    m1 = Movie(
        title="Good",
        description=lazy(lambda: get_description("去你妈的")),  # 默认永久缓存（ttl=None）
        descriptions=[
            lazy(lambda: get_description("A"), ttl=1.0),  # 缓存 1 秒
            lazy(lambda: get_description("B"), ttl=0),    # 不缓存（ttl=0）
        ],
    )
    ll=lazy(None)
    print(ll._provider==None)



    l = lazy(lambda: get_m())
    l1=lazy(lambda :get_m())

    async def ex():
        await l
    asyncio.create_task(ex)



    i = l.title     # Lazy
    i1 = l.title1   # Lazy
    print(i)        # Lazy(...) 的 repr
    print(await i1) # await 会触发 provider

    print("First call (cached/permanent):")
    print(await m1.description)
    print(await m1.description)
    print("Second call (from cache):")
    print(await m1.description)

    print("descriptions[0] (cached 1s):")
    print(await m1.descriptions[0])
    await asyncio.sleep(0.5)
    print(await m1.descriptions[0])
    print("descriptions[1] (no cache):")
    print(await m1.descriptions[1])
    print(await m1.descriptions[1])  # Will call provider again

    print("\nWaiting for cache expiry...")
    await asyncio.sleep(3)
    print("After cache expiry (permanent cache for description so still cached):")
    print(await m1.description)


if __name__ == "__main__":
    asyncio.run(main())
