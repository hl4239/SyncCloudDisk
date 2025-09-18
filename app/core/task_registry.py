# app/core/task_registry.py
from typing import Callable, Dict, Optional, Tuple, Any
from pydantic import BaseModel


# 任务函数类型约定（async）： async def fn(params: dict, progress_callback, log_callback) -> Any
JobFn = Callable[..., Any]

class _TaskEntry:
    def __init__(self, name: str, fn: JobFn, params_model: Optional[type[BaseModel]] = None):
        self.name = name
        self.fn = fn
        self.params_model = params_model

class TaskRegistry:
    def __init__(self):
        self._registry: Dict[str, _TaskEntry] = {}

    def register(self, name: Optional[str] = None, params_model: Optional[type[BaseModel]] = None):
        """
        用法：
        @registry.register("my-task", params_model=MyParamsModel)
        async def my_task(params, progress_callback, log_callback): ...
        """
        def _decorator(fn: JobFn):
            key = name or fn.__name__
            if key in self._registry:
                raise KeyError(f"task {key} already registered")
            self._registry[key] = _TaskEntry(key, fn, params_model)
            return fn
        return _decorator

    def get(self, name: str) -> _TaskEntry:
        entry = self._registry.get(name)
        if not entry:
            raise KeyError(name)
        return entry

    def list_names(self):
        return list(self._registry.keys())

# 全局单例
registry = TaskRegistry()
