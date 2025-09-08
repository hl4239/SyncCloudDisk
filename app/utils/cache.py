import inspect
import time
import asyncio
import threading
from functools import wraps
from typing import Any, Callable, Optional, List


def _make_hashable(obj: Any):
    """将任意常见 Python 对象转换为可哈希表示（递归）。"""
    if obj is None or isinstance(obj, (int, float, str, bool, bytes)):
        return obj
    if isinstance(obj, dict):
        return tuple((k, _make_hashable(v)) for k, v in sorted(obj.items()))
    if isinstance(obj, (list, tuple, set)):
        return tuple(_make_hashable(x) for x in obj)
    try:
        return repr(obj)
    except Exception:
        return ("<unhashable>", id(obj))


def async_ttl_cache(_func: Optional[Callable] = None, *, ttl: Optional[float] = None):
    """
    通用 TTL 缓存装饰器，兼容 sync/async 被装饰函数。
    用法（三种）:
        @async_ttl_cache              # 不带参数 -> 永久缓存
        async def foo(...): ...

        @async_ttl_cache()            # 等同于上面 -> 永久缓存
        def bar(...): ...

        @async_ttl_cache(ttl=10)      # 带 ttl -> 有效期 10 秒
        async def baz(...): ...
    """
    def deco(func: Callable):
        cache: dict = {}          # key -> (expire_ts_or_None, value)
        locks_async: dict = {}    # key -> asyncio.Lock
        locks_sync: dict = {}     # key -> threading.Lock
        ttl_local = ttl  # may be None => permanent

        # ---------- 异步函数 wrapper ----------
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                key = (_make_hashable(args), _make_hashable(kwargs))
                now = time.time()

                entry = cache.get(key)
                if entry:
                    expire_ts = entry[0]
                    if expire_ts is None or expire_ts > now:
                        return entry[1]

                lock = locks_async.setdefault(key, asyncio.Lock())
                async with lock:
                    # 双重检查
                    entry = cache.get(key)
                    if entry:
                        expire_ts = entry[0]
                        if expire_ts is None or expire_ts > time.time():
                            return entry[1]

                    maybe = func(*args, **kwargs)
                    # func 可能返回 coroutine 或直接返回值（兼容同步实现的情况）
                    if inspect.isawaitable(maybe):
                        val = await maybe
                    else:
                        val = maybe

                    expire_ts = None if ttl_local is None else time.time() + ttl_local
                    cache[key] = (expire_ts, val)
                    # 清理锁（避免无限增长）
                    locks_async.pop(key, None)
                    return val

            return async_wrapper

        # ---------- 同步函数 wrapper ----------
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                key = (_make_hashable(args), _make_hashable(kwargs))
                now = time.time()

                entry = cache.get(key)
                if entry:
                    expire_ts = entry[0]
                    if expire_ts is None or expire_ts > now:
                        return entry[1]

                lock = locks_sync.setdefault(key, threading.Lock())
                with lock:
                    entry = cache.get(key)
                    if entry:
                        expire_ts = entry[0]
                        if expire_ts is None or expire_ts > time.time():
                            return entry[1]

                    val = func(*args, **kwargs)
                    expire_ts = None if ttl_local is None else time.time() + ttl_local
                    cache[key] = (expire_ts, val)
                    # 清理锁（可选）
                    try:
                        del locks_sync[key]
                    except KeyError:
                        pass
                    return val

            return sync_wrapper

    # 支持两种装饰器调用形式：
    # - @async_ttl_cache        -> 此时 _func 为被装饰函数，ttl 默认为 None（永久）
    # - @async_ttl_cache(...)   -> 此时 _func 为 None，返回 deco 供后续传入函数
    if _func is None:
        return deco
    else:
        return deco(_func)


# ===== 使用示例 =====

class MovieService:
    @staticmethod
    @async_ttl_cache(ttl=10)  # 缓存 10 秒
    async def _fetch_from_api(self, movie_id: int, season: List[int]):
        print(f">>> 请求API (async): movie_id={movie_id}, season={season}")
        await asyncio.sleep(2)
        return {"latest": 12, "total": 24}

    @staticmethod
    @async_ttl_cache  # 不带参数 -> 永久缓存（注意没有括号）
    def _fetch_from_api_sync_perm(movie_id: int, season: List[int]):
        print(f">>> 请求API (sync, permanent): movie_id={movie_id}, season={season}")
        return {"latest": 100, "total": 200}

    @staticmethod
    @async_ttl_cache()  # 带空括号也表示永久缓存
    def _fetch_from_api_sync_perm2(movie_id: int, season: List[int]):
        print(f">>> 请求API (sync, permanent2): movie_id={movie_id}, season={season}")
        return {"latest": 1000, "total": 2000}

    async def get_latest_episode(self, movie_id: int, season: List[int]):
        data = self._fetch_from_api_sync_perm(movie_id, season)
        return data["latest"]

    async def get_total_episodes(self, movie_id: int, season: List[int]):
        data = self._fetch_from_api_sync_perm(movie_id, season)
        return data["total"]


# ===== 测试 =====
async def main():
    service = MovieService()
    service1 = MovieService()
    tasks = []
    tasks.append(service.get_latest_episode(1001, [1]))
    tasks.append(service1.get_total_episodes(1001, [1]))
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
