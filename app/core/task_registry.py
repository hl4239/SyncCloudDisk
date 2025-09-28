# app/core/task_registry.py
from typing import Callable, Dict, Optional, Any, Type
from pydantic import BaseModel, ValidationError
import inspect
import functools
import asyncio

# 任务函数类型约定（async）： async def fn(params: dict, progress_callback, log_callback) -> Any
JobFn = Callable[..., Any]

class _TaskEntry:
    def __init__(
        self,
        name: str,
        fn: JobFn,
        params_model: Optional[Type[BaseModel]] = None,
        original_fn: Optional[JobFn] = None,
    ):
        self.name = name
        # 存放用于实际执行的函数（可能是 wrapper）
        self.fn = fn
        # 指定或推断到的 Pydantic 模型类型（若无则为 None）
        self.params_model = params_model
        # 原始未包装的函数（便于调试/直接调用）
        self.original_fn = original_fn or fn

class TaskRegistry:
    def __init__(self):
        self._registry: Dict[str, _TaskEntry] = {}

    def register(
        self,
        name: Optional[str] = None,
        params_model: Optional[Type[BaseModel]] = None,
    ):
        """
        用法：
        @registry.register("my-task", params_model=MyParamsModel)
        async def my_task(params, progress_callback, log_callback): ...

        若不传 params_model，会尝试从函数签名中推断：
        async def my_task(params: MyParamsModel, progress_callback, log_callback): ...
        """

        def _decorator(fn: JobFn):
            key = name or fn.__name__
            if key in self._registry:
                raise KeyError(f"task {key} already registered")

            # 如果没有显式传入 model，尝试从 fn 的注解里推断 params 的类型
            inferred_model = params_model
            if inferred_model is None:
                try:
                    sig = inspect.signature(fn)
                    if "params" in sig.parameters:
                        ann = sig.parameters["params"].annotation
                        if (
                            ann is not inspect._empty
                            and isinstance(ann, type)
                            and issubclass(ann, BaseModel)
                        ):
                            inferred_model = ann
                except Exception:
                    # 不要因为推断失败而阻塞注册；只是不做自动转换
                    inferred_model = None

            # 如果没有 model，则直接注册原函数（不做包装）
            if inferred_model is None:
                entry_fn = fn
            else:
                # 创建 wrapper：接收任意额外位置/关键字参数以提高兼容性
                is_coroutine = inspect.iscoroutinefunction(fn)

                @functools.wraps(fn)
                async def _wrapped(params, progress_callback, log_callback, *args, **kwargs):
                    # 将 params 转成 model 实例
                    try:
                        if isinstance(params, dict):
                            model_instance = inferred_model(**params)
                        elif isinstance(params, BaseModel):
                            # 已经是 BaseModel 的子类实例
                            if isinstance(params, inferred_model):
                                model_instance = params
                            else:
                                # 不同模型实例：尝试 parse_obj 转换/校验
                                model_instance = inferred_model.parse_obj(params)
                        else:
                            # 其他类型（例如 dataclass、namespace、None 等），尝试 parse_obj
                            model_instance = inferred_model.parse_obj(params)
                    except ValidationError as ve:
                        # 把验证错误直接抛给调用者；调用者可以捕获并处理
                        raise ve

                    # 调用原始函数（支持 sync/async）
                    if is_coroutine:
                        return await fn(model_instance, progress_callback, log_callback, *args, **kwargs)
                    else:
                        # 在线程池中运行同步函数，避免阻塞事件循环
                        return await asyncio.to_thread(fn, model_instance, progress_callback, log_callback, *args, **kwargs)

                entry_fn = _wrapped

            # 存入 registry：用于执行的函数、原始函数、以及模型类型
            self._registry[key] = _TaskEntry(key, entry_fn, inferred_model, original_fn=fn)

            # 返回原始函数（这样装饰器对原有调用方式最无侵入）
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
