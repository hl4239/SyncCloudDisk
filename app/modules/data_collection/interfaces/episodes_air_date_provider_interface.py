import copy
from abc import ABC, abstractmethod
from typing import List

from app.database.models import  EpisodesInfo
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.utils.lazy_load import lazy

import asyncio
import inspect
import logging
from typing import Any, Set

logger = logging.getLogger(__name__)

def _format_task_info(task: asyncio.Task) -> str:
    """不等待 task，仅检查其状态与 coroutine repr。安全调用。"""
    try:
        done = task.done()
        cancelled = task.cancelled()
        # 运行中的 Task 可能没有 .get_name() in older py, guard it
        try:
            name = task.get_name()
        except Exception:
            name = None
        # 显示关联的 coroutine (不 await)
        try:
            coro = task.get_coro()
            coro_repr = repr(coro)
        except Exception:
            coro_repr = repr(task)
        return f"Task(name={name!r}, done={done}, cancelled={cancelled}, coro={coro_repr})"
    except Exception as e:
        return f"<failed to inspect task: {e!r}>"

def _inspect_lazy_instance(lazy_obj: Any) -> str:
    """生成单个 Lazy 实例的诊断字符串（不改动 lazy 状态，不 await）。"""
    parts = []
    try:
        debug_name = getattr(lazy_obj, "_debug_name", None)
        provider = getattr(lazy_obj, "_provider", None)
        try:
            prov_type = "awaitable" if inspect.isawaitable(provider) else ("callable" if callable(provider) else "value")
        except Exception:
            prov_type = "unknown"
        ttl = getattr(lazy_obj, "_ttl", None)
        cached = getattr(lazy_obj, "_cached_result", None)
        has_cached = cached is not None
        cache_time = getattr(lazy_obj, "_cache_time", None)
        running_task = getattr(lazy_obj, "_running_task", None)

        parts.append(f"Lazy debug_name={debug_name!r}")
        parts.append(f"  provider_repr={repr(provider)}")
        parts.append(f"  provider_type={prov_type}")
        parts.append(f"  ttl={ttl!r}")
        parts.append(f"  has_cached_result={has_cached} cache_time={cache_time!r}")
        if has_cached:
            # 避免打印可能很大或不可repr的 cached_result，打印类型和短 repr
            try:
                parts.append(f"  cached_result_type={type(cached).__name__} repr={repr(cached)[:400]}")
            except Exception:
                parts.append(f"  cached_result_type={type(cached).__name__} repr=<failed to repr>")
        if running_task is None:
            parts.append("  running_task=None")
        else:
            # 如果 running_task 看起来是 asyncio.Future/Task，打印状态
            if isinstance(running_task, asyncio.Task):
                parts.append("  running_task (asyncio.Task): " + _format_task_info(running_task))
            else:
                parts.append(f"  running_task (other): {repr(running_task)}")
    except Exception as e:
        parts.append(f"<failed to inspect Lazy: {e!r}>")
    return "\n".join(parts)

def debug_print_movie_data_result(obj: Any, *, max_depth: int = 3) -> None:
    """
    递归扫描一个对象（movie_data_result），打印所有检测到的 Lazy 实例的诊断信息。
    - 不会 await，不会修改对象。
    - 处理 dict/list/tuple/对象属性。
    - max_depth 防止无限递归（侧重打印一层或两层）。
    """
    seen: Set[int] = set()

    def _walk(o: Any, path: str, depth: int) -> None:
        if id(o) in seen:
            logger.debug("%s: <already seen %s>", path, type(o).__name__)
            return
        seen.add(id(o))

        # 如果这个对象 就是 Lazy（按属性识别，以兼容不同 Lazy 实现）
        if hasattr(o, "_provider") and (hasattr(o, "_running_task") or hasattr(o, "_cached_result")):
            # 认为这是 Lazy
            info = _inspect_lazy_instance(o)
            logger.warning("%s : %s", path, info)
            # 继续不深入 Lazy 的内部 provider/cached_result（以免打印大对象）
            return

        # 基本容器类型
        if depth <= 0:
            logger.debug("%s: max depth reached for %s", path, type(o).__name__)
            return

        try:
            if isinstance(o, dict):
                for k, v in o.items():
                    _walk(v, f"{path}[{k!r}]", depth - 1)
                return
            if isinstance(o, (list, tuple, set)):
                for i, v in enumerate(o):
                    _walk(v, f"{path}[{i}]", depth - 1)
                return
            # pydantic model or general object with __dict__
            if hasattr(o, "__dict__"):
                # iterate public attributes only
                for attr, val in vars(o).items():
                    _walk(val, f"{path}.{attr}", depth - 1)
                return
            # fallback: stop at primitives
            logger.debug("%s: leaf %s", path, repr(o)[:200])
        except Exception as e:
            logger.exception("Exception while walking %s: %s", path, e)

    # start
    logger.warning(">>> DEBUG dump of movie_data_result (max_depth=%d) BEGIN", max_depth)
    _walk(obj, "movie_data_result", max_depth)
    logger.warning(">>> DEBUG dump END")
class IEpisodesAirDateProvider(ABC):
    @abstractmethod
    async def get_air_date(self,movie_data_source:MovieDataSourceResult) ->  List[EpisodesInfo]:
        ...

    async def set_air_date(self,movie_data_result:MovieDataSourceResult):
        """
        对已存在的episodes_infos补充air_date,不会创建新的或改变长度

        :param movie_data_result:
        :return:
        """

        try:
            copy_movie_data = copy.deepcopy(movie_data_result)
            movie_data_result.episodes_info = lazy(lambda c=copy_movie_data: self.get_air_date(c))
        except Exception as e:
            # 先记录原始异常（含 traceback）
            logger.exception("deepcopy(movie_data_result) failed: %s", e)

            # 打印整个 movie_data_result 中的 Lazy 对象状态（递归层级可调）
            debug_print_movie_data_result(movie_data_result, max_depth=3)

            # # 如果你只想打印特定属性（例如 episodes_info / title_season / tmdb_infos）
            # try:
            #     for name in ("episodes_info", "title_season", "tmdb_infos", "description"):
            #         if hasattr(movie_data_result, name):
            #             val = getattr(movie_data_result, name)
            #             if hasattr(val, "_provider") and (
            #                     hasattr(val, "_running_task") or hasattr(val, "_cached_result")):
            #                 logger.warning("Direct attribute %s: %s", name, _inspect_lazy_instance(val))
            # except Exception:
            #     logger.exception("failed to inspect selected attrs")

            # 之后按你的需求决定：重新 raise 或继续处理
            raise
