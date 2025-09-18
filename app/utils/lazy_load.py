# example_lazy_pydantic_with_helper.py
from __future__ import annotations
import asyncio
import time
import inspect
from typing import (
    Any, Awaitable, Callable, Generic, Optional, TypeVar, Union, overload, List
)
import typing

from app.utils.cache import async_ttl_cache

T = TypeVar("T")
Provider = Union[Callable[[], Union[T, Awaitable[T]]], Awaitable[T], T]


# ---------------- Lazy implementation with optional caching ----------------
class Lazy(Generic[T]):
    """
    Lazy wrapper with optional caching:
      - provider: callable/awaitable/value
      - ttl: cache TTL in seconds, None means no cache, default enables cache with 60s TTL
      - await lazy -> 调用 provider 并返回结果（根据 ttl 决定是否缓存）
      - 并发期间复用同一个正在运行的 Task，任务完成后根据 ttl 决定是否保留结果
      - 支持 __getitem__ 返回 awaitable（方便 await model.descriptions[0]）
      - 提供 pydantic v1/v2 的 hook，以便 runtime 把原始输入包装为 Lazy
    """
    __slots__ = ("_provider", "_running_task", "_ttl", "_cached_result", "_cache_time")

    def __init__(self, provider: Provider[T], ttl: Optional[float] = 60.0):
        self._provider = provider
        self._running_task: Optional[asyncio.Task] = None
        self._ttl = ttl  # None means no cache, float means cache with TTL
        self._cached_result: Optional[T] = None
        self._cache_time: Optional[float] = None

    @classmethod
    def wrap(cls, provider: Provider[T], ttl: Optional[float] = 60.0) -> "Lazy[T]":
        if isinstance(provider, Lazy):
            # If already Lazy, preserve its TTL unless explicitly overridden
            return provider if ttl == 60.0 else cls(provider._provider, ttl)
        return cls(provider, ttl)

    def _is_cache_valid(self) -> bool:
        """Check if cached result is still valid"""
        if self._ttl is None or self._cached_result is None or self._cache_time is None:
            return False
        return time.time() - self._cache_time < self._ttl

    async def _call_provider(self) -> T:
        prov = self._provider
        if inspect.isawaitable(prov):
            return await prov
        if callable(prov):
            maybe = prov()
            if inspect.isawaitable(maybe):
                return await maybe
            else:
                return maybe
        return prov

    async def _ensure_run(self) -> T:
        # Check cache first
        if self._is_cache_valid():
            return self._cached_result

        # If already running, wait for it
        if self._running_task is not None:
            return await self._running_task

        # Start new task
        loop = asyncio.get_running_loop()
        task = loop.create_task(self._call_provider())
        self._running_task = task

        try:
            res = await task

            # Cache result if TTL is set
            if self._ttl is not None:
                self._cached_result = res
                self._cache_time = time.time()

            return res
        finally:
            # Clear running task
            self._running_task = None

    def __await__(self):
        return self._ensure_run().__await__()

    def __getitem__(self, idx):
        async def _get_index():
            val = await self._ensure_run()
            return val[idx]

        return _get_index()

    def __repr__(self) -> str:
        return f"Lazy(provider={self._provider!r}, ttl={self._ttl})"

    # 运行时：pydantic v1 validator hook
    @classmethod
    def _wrap_input(cls, v: Any, ttl: Optional[float] = 60.0):
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
# 使用 overload 提供类型信息，帮助编辑器/类型检查器推断 Lazy[T]
@overload
def lazy(provider: Callable[[], Awaitable[T]], *, ttl: Optional[float] = 60.0) -> Lazy[T]: ...


@overload
def lazy(provider: Callable[[], T], *, ttl: Optional[float] = 60.0) -> Lazy[T]: ...


@overload
def lazy(awaitable: Awaitable[T], *, ttl: Optional[float] = 60.0) -> Lazy[T]: ...


@overload
def lazy(value: T, *, ttl: Optional[float] = 60.0) -> Lazy[T]: ...


def lazy(provider: Provider[T], *, ttl: Optional[float] = 60.0) -> Lazy[T]:
    """
    编辑器友好的包装器：在构造模型时请用 lazy(lambda: ...) 来让类型检查器知道字段是 Lazy[T]。
    运行时也可以直接把 callable / coroutine / 值 传给 pydantic 构造函数（pydantic 会自动 wrap），
    但是那样编辑器通常会报类型不匹配（因为静态检查器看不到 pydantic 的运行时包装）。

    Args:
        provider: The provider function/awaitable/value
        ttl: Cache TTL in seconds. None means no cache, default is 60 seconds
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
    # 编辑器/类型系统看到的是 Lazy[str] | None（如果你使用 lazy(...) 来传参）
    description: Optional[Lazy[str]] = None
    # descriptions 是 list[Lazy[str]]：每个元素是独立 provider（你想要的语义）
    descriptions: Optional[List[Lazy[str]]] = None


# ---------------- Demo main ----------------
async def main():
    # 推荐做法（编辑器友好）：
    # 使用 helper lazy(...) 使得静态类型检查器/IDE 能推断为 Lazy[str]
    m1 = Movie(
        title="Good",
        description=lazy(lambda: get_description("去你妈的")),  # 默认缓存 60 秒
        descriptions=[
            lazy(lambda: get_description("A"), ttl=1.0),  # 缓存 10 秒
            lazy(lambda: get_description("B"), ttl=None),  # 不缓存
        ]
    )

    print("First call (cached):")
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

    # Test cache expiry
    print("\nWaiting for cache expiry...")
    await asyncio.sleep(3)  # Wait for external cache to expire
    print("After cache expiry:")
    print(await m1.description)  # Should still be cached in Lazy (60s TTL)


if __name__ == "__main__":
    asyncio.run(main())