from typing import TypeVar, Generic, Union, List, AsyncIterable, AsyncIterator, Sequence, Optional
import asyncio
import inspect

T = TypeVar("T")

def _is_sequence(obj) -> bool:
    return isinstance(obj, Sequence) and not isinstance(obj, (str, bytes))

#
# AsyncCachedIterator: 单独保留并做了健壮处理
#
async def _empty_async_cached_iterator():
    return  AsyncCachedIterator([])

class AsyncCachedIterator(Generic[T]):
    """
    Accepts Sequence[T] (list/tuple) or AsyncIterable[T] (including async generators).
    First full traversal caches items; subsequent traversals read from cache.
    """
    def __init__(self, source: Union[Sequence[T], AsyncIterable[T]]):
        self._source = source
        self._cache: List[T] = []
        self._is_consumed = False
        self._lock = asyncio.Lock()
        self._aiter: Optional[AsyncIterator[T]] = None

        # lazy detection: do not construct aiters until needed

        # basic validation
        if not (_is_sequence(source) or hasattr(source, "__aiter__")):
            if inspect.isawaitable(source):
                raise TypeError("如果传入 coroutine，请先 await 它以获得 Sequence 或 AsyncIterable")
            raise TypeError("source 必须是 Sequence（list/tuple）或 AsyncIterable")

    def __aiter__(self):
        return _CachedIteratorView(self)

    async def _make_aiter_if_needed(self):
        if self._aiter is None:
            src = self._source
            if _is_sequence(src):
                async def _seq_gen(seq):
                    for x in seq:
                        yield x
                self._aiter = _seq_gen(src)  # type: ignore[assignment]
            else:
                self._aiter = src.__aiter__()  # type: ignore[assignment]

    async def _close_underlying(self):
        if self._aiter is not None and getattr(self._aiter, "aclose", None):
            try:
                await self._aiter.aclose()
            except Exception:
                pass


class _CachedIteratorView(Generic[T]):
    def __init__(self, parent: AsyncCachedIterator[T]):
        self._parent = parent
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        # 先尝试从缓存读取（无锁）
        if self._index < len(self._parent._cache):
            item = self._parent._cache[self._index]
            self._index += 1
            return item

        # 进入锁，只有一个协程可以去拉取底层元素并追加缓存
        async with self._parent._lock:
            # 再检查缓存
            if self._index < len(self._parent._cache):
                item = self._parent._cache[self._index]
                self._index += 1
                return item

            if self._parent._is_consumed:
                raise StopAsyncIteration

            # 确保 aiters 已准备好
            await self._parent._make_aiter_if_needed()

            try:
                # 从异步迭代器取下一个元素
                try:
                    _anext = anext  # type: ignore[name-defined]
                except Exception:
                    item = await self._parent._aiter.__anext__()  # type: ignore[attr-defined]
                else:
                    item = await _anext(self._parent._aiter)  # type: ignore[call-arg]

                # 缓存并返回
                self._parent._cache.append(item)
                self._index += 1
                return item
            except StopAsyncIteration:
                self._parent._is_consumed = True
                await self._parent._close_underlying()
                raise
            except Exception:
                # 出现其它异常也把源视为耗尽并尝试关闭
                self._parent._is_consumed = True
                await self._parent._close_underlying()
                raise

#
# AsyncMergedCachedIterator: 保留并支持接收 AsyncCachedIterator
#
class AsyncMergedCachedIterator(Generic[T]):
    """
    合并多个 sources：Sequence[T]、AsyncIterable[T] 或 AsyncCachedIterator[T]。
    mode: "concat" 或 "interleave"（轮询）
    """
    def __init__(self, sources: List[Union[Sequence[T], AsyncIterable[T], AsyncCachedIterator[T]]], mode: str = "concat"):
        if mode not in ("concat", "interleave"):
            raise ValueError("mode must be 'concat' or 'interleave'")
        if not sources:
            raise ValueError("至少需要一个 source")
        self._sources = sources
        self._mode = mode

        self._aiters: List[Optional[AsyncIterator[T]]] = [None] * len(sources)
        self._done: List[bool] = [False] * len(sources)
        self._cache: List[T] = []
        self._is_consumed = False
        self._lock = asyncio.Lock()
        self._concat_idx = 0
        self._next_idx = 0

    def __aiter__(self):
        return _MergedView(self)

    def _make_aiter_from_source(self, src) -> AsyncIterator[T]:
        # 如果是 AsyncCachedIterator，直接调用它的 __aiter__() 保持其缓存语义
        if isinstance(src, AsyncCachedIterator):
            return src.__aiter__()  # type: ignore[return-value]
        if _is_sequence(src):
            async def _seq_gen(seq):
                for x in seq:
                    yield x
            return _seq_gen(src)
        if hasattr(src, "__aiter__"):
            return src.__aiter__()  # type: ignore[return-value]
        if inspect.isawaitable(src):
            raise TypeError("传入了 awaitable，请先 await 获取实际的 Sequence 或 AsyncIterable")
        raise TypeError("source 必须是 Sequence、AsyncIterable、或 AsyncCachedIterator")

    async def _get_aiter(self, idx: int) -> AsyncIterator[T]:
        if self._aiters[idx] is None:
            self._aiters[idx] = self._make_aiter_from_source(self._sources[idx])
        return self._aiters[idx]

    async def _fetch_next_from_source(self, idx: int):
        ait = await self._get_aiter(idx)
        try:
            try:
                _anext = anext  # type: ignore[name-defined]
            except Exception:
                item = await ait.__anext__()  # type: ignore[attr-defined]
            else:
                item = await _anext(ait)  # type: ignore[call-arg]
            return item
        except StopAsyncIteration:
            self._done[idx] = True
            # 尝试关闭
            aclose = getattr(ait, "aclose", None)
            if aclose:
                try:
                    await aclose()
                except Exception:
                    pass
            raise

    async def _fetch_next(self):
        n = len(self._sources)
        if self._mode == "concat":
            while self._concat_idx < n and self._done[self._concat_idx]:
                self._concat_idx += 1
            if self._concat_idx >= n:
                self._is_consumed = True
                raise StopAsyncIteration
            try:
                item = await self._fetch_next_from_source(self._concat_idx)
                return item
            except StopAsyncIteration:
                return await self._fetch_next()
        else:  # interleave
            for _ in range(n):
                idx = self._next_idx
                self._next_idx = (self._next_idx + 1) % n
                if self._done[idx]:
                    continue
                try:
                    item = await self._fetch_next_from_source(idx)
                    return item
                except StopAsyncIteration:
                    continue
            self._is_consumed = True
            raise StopAsyncIteration


class _MergedView(Generic[T]):
    def __init__(self, parent: AsyncMergedCachedIterator[T]):
        self._parent = parent
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        # 尝试从 cache
        if self._index < len(self._parent._cache):
            item = self._parent._cache[self._index]
            self._index += 1
            return item

        async with self._parent._lock:
            if self._index < len(self._parent._cache):
                item = self._parent._cache[self._index]
                self._index += 1
                return item

            if self._parent._is_consumed:
                raise StopAsyncIteration

            item = await self._parent._fetch_next()
            self._parent._cache.append(item)
            self._index += 1
            return item

#
# 演示：两个 AsyncCachedIterator，然后合并一次遍历（interleave 与 concat）并展示缓存效果
#
async def slow_gen(name, delay, count):
    for i in range(1, count + 1):
        await asyncio.sleep(delay)
        print(f"[{name}] produced {i}")
        yield f"{name}{i}"
async def quick_gen():
    return [1,2,3]

async def demo():
    # 一个异步生成器作为底层源（会在打印中看到只在第一次被拉取时输出 produced）
    a_src = slow_gen("A", 0.15, 4)
    # 一个同步 list 作为源
    b_list = [100, 200, 300]

    # 把它们分别装成 AsyncCachedIterator（可选，但展示怎样同时保留两个类）
    cached_a = AsyncCachedIterator(a_src)
    cached_b = AsyncCachedIterator(b_list)
    cached_c=AsyncCachedIterator(await quick_gen())
    # 合并：interleave（轮询）
    merged = AsyncMergedCachedIterator([cached_a, cached_b,cached_c], mode="interleave")
    print("=== first traversal (merged interleave) ===")
    async for item in merged:
        print("merged ->", item)

    print("\n=== second traversal of merged (should read from cache, no more 'produced' prints) ===")
    async for item in merged:
        print("merged cached ->", item)

    print("\n=== direct traversal of cached_a (should read from cache too) ===")
    async for item in cached_a:
        print("cached_a ->", item)

    # 演示 concat
    cached_c = AsyncCachedIterator(slow_gen("C", 0.08, 3))
    merged2 = AsyncMergedCachedIterator([b_list, cached_c], mode="concat")
    print("\n=== merged concat first traversal ===")
    async for item in merged2:
        print("merged2 ->", item)

    print("\n=== merged2 second traversal (cached) ===")
    async for item in merged2:
        print("merged2 cached ->", item)


if __name__ == "__main__":
    asyncio.run(demo())
