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


# ---------------- Lazy implementation (no permanent cache) ----------------
class Lazy(Generic[T]):
    """
    Lazy wrapper:
      - provider: callable/awaitable/value
      - await lazy -> 调用 provider 并返回结果（不在 Lazy 内部永久缓存）
      - 并发期间复用同一个正在运行的 Task，任务完成后清理
      - 支持 __getitem__ 返回 awaitable（方便 await model.descriptions[0]）
      - 提供 pydantic v1/v2 的 hook，以便 runtime 把原始输入包装为 Lazy
    """
    __slots__ = ("_provider", "_running_task")

    def __init__(self, provider: Provider[T]):
        self._provider = provider
        self._running_task: Optional[asyncio.Task] = None

    @classmethod
    def wrap(cls, provider: Provider[T]) -> "Lazy[T]":
        if isinstance(provider, Lazy):
            return provider
        return cls(provider)

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
        if self._running_task is not None:
            return await self._running_task
        loop = asyncio.get_running_loop()
        task = loop.create_task(self._call_provider())
        self._running_task = task
        try:
            res = await task
            return res
        finally:
            # 不在 Lazy 内部缓存结果：清理 running_task
            self._running_task = None

    def __await__(self):
        return self._ensure_run().__await__()

    def __getitem__(self, idx):
        async def _get_index():
            val = await self._ensure_run()
            return val[idx]
        return _get_index()

    def __repr__(self) -> str:
        return f"Lazy(provider={self._provider!r})"

    # 运行时：pydantic v1 validator hook
    @classmethod
    def _wrap_input(cls, v: Any):
        if isinstance(v, Lazy):
            return v
        if inspect.isawaitable(v):
            return Lazy(v)
        if callable(v):
            return Lazy(v)
        return Lazy(lambda: v)

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
def lazy(provider: Callable[[], Awaitable[T]]) -> Lazy[T]: ...
@overload
def lazy(provider: Callable[[], T]) -> Lazy[T]: ...
@overload
def lazy(awaitable: Awaitable[T]) -> Lazy[T]: ...
@overload
def lazy(value: T) -> Lazy[T]: ...

def lazy(provider: Provider[T]) -> Lazy[T]:
    """
    编辑器友好的包装器：在构造模型时请用 lazy(lambda: ...) 来让类型检查器知道字段是 Lazy[T]。
    运行时也可以直接把 callable / coroutine / 值 传给 pydantic 构造函数（pydantic 会自动 wrap），
    但是那样编辑器通常会报类型不匹配（因为静态检查器看不到 pydantic 的运行时包装）。
    """
    return Lazy.wrap(provider)


    # ---------------- Example async provider (with ttl cache) ----------------
@async_ttl_cache(ttl=2.0)
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
        description=lazy(lambda: get_description("去你妈的")),   # 编辑器会认为这是 Lazy[str]
        descriptions=[
            lazy(lambda: get_description("A")),
            lazy(lambda: get_description("B")),
        ]
    )
    print(await m1.description)
    print(await m1.descriptions[0])




if __name__ == "__main__":
    asyncio.run(main())
