import inspect
import time
import asyncio
import threading
from functools import wraps
from typing import Any, Callable, Optional, Sequence, Union, Tuple, Dict
from dataclasses import is_dataclass, asdict
from datetime import datetime, date, time as dtime
from enum import Enum
import json
# 获取字段名集合，兼容 Pydantic v1/v2
from pydantic import BaseModel

def _get_model_fields(model: BaseModel):
    cls = model.__class__
    if hasattr(cls, "model_fields"):  # Pydantic v2
        return cls.model_fields
    return getattr(cls, "__fields__")  # 只在 v1 存在


# ---------- 辅助：把任意常见对象转成稳定的“可哈希”表示 ----------
def _make_hashable(obj: Any):
    """把常见 Python 对象递归转为稳定的可哈希表示（用于缓存 key）。"""
    # 基本不可变类型直接返回
    if obj is None or isinstance(obj, (int, float, str, bool)):
        return obj

    # bytes / bytearray -> 十六进制表示
    if isinstance(obj, (bytes, bytearray)):
        return ("__bytes__", bytes(obj).hex())

    # datetime-like -> isoformat
    if isinstance(obj, (datetime, date, dtime)):
        return ("__datetime__", obj.isoformat())

    # Enum -> 使用 value
    if isinstance(obj, Enum):
        return ("__enum__", obj.__class__.__name__, _make_hashable(obj.value))

    # pydantic BaseModel -> 转 dict 再处理（稳定）
    if isinstance(obj, BaseModel):
        # 你可以调整 exclude_unset/exclude_defaults/exclude_none 等参数
        try:
            return _make_hashable(obj.dict())
        except Exception:
            # 退回到 repr
            return ("__repr__", repr(obj))

    # dataclass -> 转 dict
    if is_dataclass(obj):
        try:
            return _make_hashable(asdict(obj))
        except Exception:
            pass

    # dict -> 按键排序后递归
    if isinstance(obj, dict):
        return tuple((k, _make_hashable(v)) for k, v in sorted(obj.items()))

    # list/tuple -> tuple
    if isinstance(obj, (list, tuple)):
        return tuple(_make_hashable(x) for x in obj)

    # set -> 排序后 tuple
    if isinstance(obj, set):
        try:
            return tuple(_make_hashable(x) for x in sorted(obj, key=lambda e: repr(e)))
        except Exception:
            return tuple(_make_hashable(x) for x in obj)

    # 尝试 JSON 序列化（保证 sort_keys=True）
    try:
        return ("__json__", json.dumps(obj, default=lambda o: getattr(o, "__dict__", repr(o)), sort_keys=True))
    except Exception:
        pass

    # 最后退回 repr（可读），实在不行再用 id
    try:
        return ("__repr__", repr(obj))
    except Exception:
        return ("<unhashable>", id(obj))


def _get_attr_nested(obj: Any, parts: Sequence[str]):
    """支持点路径取值"""
    cur = obj
    for p in parts:
        if cur is None:
            return None
        if isinstance(cur, BaseModel):
            fields = _get_model_fields(cur)
            if p in fields:
                cur = getattr(cur, p, None)
            else:
                return None
        else:
            try:
                cur = getattr(cur, p, None)
            except Exception:
                return None
    return cur


def _extract_key_from_args(
    key_fields: Union[str, Sequence[str]],
    args: tuple,
    kwargs: dict
):
    """从 args/kwargs 中提取多个字段值"""
    fields = [key_fields] if isinstance(key_fields, str) else list(key_fields)
    results = []

    for field in fields:
        parts = field.split(".")
        found = None

        # 先从 kwargs 里找
        for v in kwargs.values():
            if isinstance(v, BaseModel):
                found = _get_attr_nested(v, parts)
            elif hasattr(v, parts[0]):
                found = _get_attr_nested(v, parts)
            if found is not None:
                break

        # 再从 args 里找
        if found is None:
            for a in args:
                if isinstance(a, BaseModel):
                    found = _get_attr_nested(a, parts)
                elif hasattr(a, parts[0]):
                    found = _get_attr_nested(a, parts)
                if found is not None:
                    break

        results.append(found)

    return tuple(results) if len(results) > 1 else results[0]

# ---------- 改造后的装饰器，实现 key_fields / key_func ----------
def async_ttl_cache(
    _func: Optional[Callable] = None,
    *,
    ttl: Optional[float] = None,
    key_fields: Optional[Union[str, Sequence[str]]] = None,
    key_func: Optional[Callable[..., Any]] = None,
):
    """
    支持三种调用方式：
      @async_ttl_cache
      @async_ttl_cache()
      @async_ttl_cache(ttl=10, key_fields="douban_id")
    参数：
      ttl: 缓存过期秒数（None 表示永久缓存）
      key_fields: 字符串或字符串序列，从调用参数中提取字段作为唯一 key（支持点路径）
      key_func: 自定义函数 key_func(*args, **kwargs) -> 原始 key 值（会被 _make_hashable）
    """
    def deco(func: Callable):
        cache: Dict[Any, Tuple[Optional[float], Any]] = {}   # key -> (expire_ts_or_None, value)
        locks_async: Dict[Any, asyncio.Lock] = {}            # key -> asyncio.Lock
        locks_sync: Dict[Any, threading.Lock] = {}           # key -> threading.Lock
        ttl_local = ttl

        def build_key(args, kwargs):
            # 优先 key_func
            if key_func is not None:
                try:
                    raw = key_func(*args, **kwargs)
                except Exception:
                    raw = (args, kwargs)
                return (func.__module__, func.__qualname__, _make_hashable(raw))

            # 然后 key_fields
            if key_fields is not None:
                try:
                    raw = _extract_key_from_args(key_fields, args, kwargs)
                    # 如果 raw 是 None（未找到），回退成 args/kwargs 的整体
                    if raw is None:
                        raw = (args, kwargs)
                except Exception:
                    raw = (args, kwargs)
                return (func.__module__, func.__qualname__, _make_hashable(raw))

            # 默认：把 args/kwargs 全部作为 key
            return (func.__module__, func.__qualname__, _make_hashable((args, kwargs)))

        # ---------- 异步函数 wrapper ----------
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                key = build_key(args, kwargs)
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
                    # func 可能返回 coroutine 或直接返回值（以兼容）
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
                key = build_key(args, kwargs)
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

    # 支持两种装饰器写法
    if _func is None:
        return deco
    else:
        return deco(_func)

from pydantic import BaseModel

class Movie(BaseModel):
    douban_id: str
    title: Optional[str] = None
    season: Optional[int] = None

# 使用 key_fields = "douban_id"（从第一个参数的 pydantic Movie 中抽取 douban_id）
@async_ttl_cache(ttl=5, key_fields=['douban_id', 'title'])
async def fetch_for_movie(movie: Movie):
    print(">>> 实际请求：fetch_for_movie", movie.douban_id)
    await asyncio.sleep(0.5)
    return {"data": movie.douban_id, "ts": time.time()}
@async_ttl_cache(ttl=5, key_fields=['douban_id', 'title'])
async def fetch_for_movie1(movie: Movie):
    print(">>> 实际请求：fetch_for_movie1", movie.douban_id)
    await asyncio.sleep(0.5)
    return {"data": movie.douban_id, "ts": time.time()}
# 使用 key_func 自定义 key（也可做哈希或屏蔽敏感字段）
def my_key_func(*args, **kwargs):
    # 尝试从 kwargs 或 args 中取 movie.douban_id
    movie = kwargs.get("movie") or (args[0] if args else None)
    if isinstance(movie, BaseModel):
        return movie.douban_id
    return repr((args, kwargs))

@async_ttl_cache(ttl=5, key_func=my_key_func)
async def fetch_with_keyfunc(movie: Movie):
    print(">>> 实际请求：fetch_with_keyfunc", movie.douban_id)
    await asyncio.sleep(0.5)
    return {"data": movie.douban_id, "ts": time.time()}

async def main():
    m1 = Movie(douban_id="id-123", title=None)
    m2 = Movie(douban_id="id-123", title='a')
    # m1 和 m2 虽为不同实例，但 key_fields 指向 douban_id，会命中缓存
    r1 = await fetch_for_movie(m1)
    r2 = await fetch_for_movie(m2)
    print("r1 == r2 ?", r1 == r2)
    # key_func 示例
    s1 = await fetch_with_keyfunc(m1)
    s2 = await fetch_with_keyfunc(m2)
    print("s1 == s2 ?", s1 == s2)

    # 等待过期后再次请求（演示 ttl 生效）
    await asyncio.sleep(6)
    r3 = await fetch_for_movie(m1)
    print("r3 fetched after ttl:", r3)
# ============== 使用示例与简单测试 ==============

if __name__ == "__main__":


    asyncio.run(main())
