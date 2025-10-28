# pipeline_example.py
import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from app.utils.lazy_load import Lazy


# ------------------ pipeline core ------------------
def pipeline_task(name: Optional[str] = None,
                  *,
                  order: int = 0,
                  provides: Optional[Sequence[str]] = None,
                  batch: bool = False):
    """
    用于标注 pipeline 步骤的装饰器（可用于 sync/async 函数）
    - name: 任务名称，若为 None 则使用函数名
    - order: 执行顺序（越小越先）
    - provides: 本步骤会填充的字段名列表（用于跳过已填充项）
    - batch: True 表示一次接收 List[item]，False 表示逐条接收单个 item
    """
    provides = tuple(provides or ())

    def deco(func: Callable):
        meta = {
            "name": name or func.__name__,
            "order": order,
            "provides": provides,
            "batch": batch
        }
        setattr(func, "_pipeline_meta", meta)
        return func

    return deco

def _field_is_assigned_without_trigger(item: Any, field: str) -> bool:
    """
    在不触发描述符 __get__ 的情况下判断 field 是否已经被“赋值且不为 None”。
    返回 True 表示该字段已存在并且其值不是 None（即不缺失）。
    返回 False 表示没有赋值（或值为 None）——需要执行填充逻辑。
    兼容两种情况：
      1. 如果类对该属性使用了 AsyncLazyProperty（或类似 descriptor），
         我们检查 descriptor 的内部缓存/override 属性 (_lazy_cache_<name>, _lazy_override_<name>)；
         如果这些内部标记存在且值不是 None，则认为已赋值。
         如果只有 provider 存在而 cache/override 不存在，则认为还未赋值（不触发 provider）。
      2. 否则回退到实例字典 vars(item)，只按 None 判断（不触发 descriptor）。
    """
    # 1) 先尝试从类属性上拿 descriptor（不会触发 __get__）
    desc = getattr(type(item), field, None)

    # 如果类上存在 AsyncLazyProperty-like 描述符（有 cache_attr/override_attr/provider_attr）
    if desc is not None and all(hasattr(desc, a) for a in ("cache_attr", "override_attr", "provider_attr")):
        cache_name = desc.cache_attr
        override_name = desc.override_attr
        provider_name = desc.provider_attr

        # 优先检查 override（实例级显式赋值）
        if hasattr(item, override_name):
            val = getattr(item, override_name)
            return val is not None

        # 再检查缓存
        if hasattr(item, cache_name):
            val = getattr(item, cache_name)
            return val is not None

        # provider 存在但没有缓存/override -> 视为尚未获得实际值（不触发 provider）
        if hasattr(item, provider_name):
            return False

        # descriptor 存在但没有任何实例内部数据 -> 未赋值
        return False

    # 2) 回退：直接检查实例 __dict__（不会触发 descriptor）
    inst_vars = vars(item)
    if field in inst_vars:
        return inst_vars[field] is not None

    # 属性既不在 __dict__，也不是 AsyncLazyProperty 的缓存/override -> 视为未赋值
    return False


def _item_missing_provides(item: Any, provides: Sequence[str]) -> bool:
    """
    返回 True 表示该 item 在 provides 指定的任意字段上缺失（需执行该 task）。
    这里的“缺失”严格按 None 判断（即仅当字段不存在或为 None 时视为缺失）。
    """
    if not provides:
        return True

    for f in provides:
        if not _field_is_assigned_without_trigger(item, f):
            # 只要某个提供字段没被赋值（或为 None），就认为需要执行该步骤
            return True
    # 所有字段都已存在且都不是 None
    return False



class Pipeline:
    def __init__(self):
        # tasks: list of tuples (order, name, func, provides, batch)
        self._tasks: List[Tuple[int, str, Callable, Tuple[str, ...], bool]] = []

    def register_from(self, owner: Any):
        """
        扫描并注册 owner（通常是 self）的实例方法。
        装饰器把 meta 挂在原始函数上（func._pipeline_meta），method 是 bound method，
        需要通过 method.__func__ 访问原始函数对象上的 meta。
        """
        for _, method in inspect.getmembers(owner, predicate=inspect.ismethod):
            func = getattr(method, "__func__", None) or method
            meta = getattr(func, "_pipeline_meta", None)
            if meta:
                # 注册 bound method (method) 作为要调用的 func，
                # 但 meta 存在于 func（未绑定的函数）上
                self._tasks.append((meta["order"], meta["name"], method, tuple(meta["provides"]), meta["batch"]))
        # 保证按 order 排序并去重（可选）
        self._tasks.sort(key=lambda t: t[0])
    def register(self, func: Callable):
        """注册单个已用 @pipeline_task 标注的函数"""
        meta = getattr(func, "_pipeline_meta", None)
        if not meta:
            raise ValueError("func is not decorated with @pipeline_task")
        self._tasks.append((meta["order"], meta["name"], func, tuple(meta["provides"]), meta["batch"]))
        self._tasks.sort(key=lambda t: t[0])

    def register_from_module(self, namespace: Dict[str, Any]):
        """扫描并注册 module-level 函数（传入 globals()）"""
        for obj in namespace.values():
            if inspect.iscoroutinefunction(obj) or inspect.isfunction(obj):
                meta = getattr(obj, "_pipeline_meta", None)
                if meta:
                    self._tasks.append((meta["order"], meta["name"], obj, tuple(meta["provides"]), meta["batch"]))
        self._tasks.sort(key=lambda t: t[0])

    async def _maybe_call(self, func: Callable, *args, **kwargs):
        """支持 sync/async 调用"""
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    def _find_entry(self, entry_name: str):
        for order, name, func, provides, batch in self._tasks:
            if name == entry_name:
                return (order, name, func, provides, batch)
        return None

    async def run(self, entry: str, *entry_args, **entry_kwargs):
        entry_meta = self._find_entry(entry)
        if not entry_meta:
            registered = [name for _, name, *_ in self._tasks]
            raise RuntimeError(f"Pipeline entry '{entry}' not found. Registered: {registered}")

        entry_order, _, entry_func, _, _ = entry_meta  # <- 获取 entry 的 order
        items = await self._maybe_call(entry_func, *entry_args, **entry_kwargs)

        # 统一把单个 item 封装成 list 以便后续处理
        single_return = False
        if items is None:
            return None
        if not isinstance(items, list):
            single_return = True
            items = [items]

        # 遍历后续任务（按 order），只执行 order > entry_order 的任务
        for order, name, func, provides, batch in self._tasks:
            if order <= entry_order:
                continue  # 跳过 entry 本身以及所有与 entry 同 order 的任务

            # 计算需要处理的 item 子集（若 provides 非空，则仅那些缺失相应字段的 item）
            needs = []
            if provides:
                for item in items:
                    if _item_missing_provides(item, provides):
                        needs.append(item)
            else:
                needs = items

            if not needs:
                continue

            if batch:
                # batch 模式一次接收 List[item]
                await self._maybe_call(func, needs)
            else:
                # per-item 模式：并发执行每项任务
                coros = [self._maybe_call(func, it) for it in needs]
                await asyncio.gather(*coros)

        # 解包返回与 entry 返回类型一致
        return items[0] if single_return else items


# ------------------ 使用示例（你的 model + 函数） ------------------

class MyModel:
    user_id: Lazy[int]= None
    file_data: Lazy[list]= None
    api_data: Lazy[list]= None
    combined:  Lazy[list]= None
    modified:  Lazy[list]= None
    loaded: Lazy[bool] = False
    is_called:Lazy[bool] = False
class ExamplePipeline:
    def __init__(self):
        self.pipeline = Pipeline()
        self.pipeline.register_from(self)


    # 用装饰器标注模块级函数（注意：这里装饰器仅写 meta，不直接注册）
    @pipeline_task(name='entry_0', order=0, batch=False)
    async def entry_create(self,user_token: str):

        m = MyModel()
        print('entry_create0 执行')
        if user_token:
            m.user_id = int(user_token.split("-")[-1])
            m.file_data = [f"file_for_{m.user_id}"]
        return m

    @pipeline_task(name='entry_1', order=0, batch=False)
    async def entry_create1(self,user_token: str):
        async def is_called():
            print('已加载')
            return True
        m = MyModel()
        print('entry_create1 执行')
        if user_token:
            m.user_id = int( user_token.split("-")[-1])
            m.file_data = [f"file_for_{await m.user_id}"]
            m.api_data = [f"api_for_{await m.user_id}"]
            m.is_called = lambda: is_called()
        m1 = MyModel()
        print('entry_create1 执行')
        if user_token:
            m1.user_id = int(user_token.split("-")[-1])
            m1.file_data = [f"file_for_{await m1.user_id}"]
            m1.api_data = [f"api_for_{await m1.user_id}"]
            m1.is_called = lambda: is_called()

        return [m,m1]

    @pipeline_task(name='extract_file', order=10, batch=False, provides=('file_data','is_called'))
    async def extract_file(self,model: MyModel):
        print("extract_file 执行 for",await model.user_id)
        # 仅在 file_data 缺失时才会被调用（由于 provides 指定了 'file_data'）
        model.file_data = [f"file_for_{await model.user_id}________========="]
        return model

    @pipeline_task(name='extract_api', order=20, batch=False, provides=('api_data',))
    async def extract_api(self,model: MyModel):
        print("extract_api 执行 for",await model.user_id)
        model.api_data = [f"api_for_{await model.user_id}"]
        return model

    @pipeline_task(name='transform', order=30, batch=False, provides=('combined',))
    async def transform(self,model: MyModel):
        print("transform 执行 for",await model.user_id)
        model.combined =await model.file_data +await model.api_data
        return model

    @pipeline_task(name='new_transform', order=40, batch=False, provides=('modified',))
    async def new_transform(self,model: MyModel):
        print("new_transform 执行 for",await model.user_id)
        model.modified = [f"modified_{x}" for x in await model.combined]
        return model

    @pipeline_task(name='load', order=50, batch=True, provides=('loaded',))
    async def load(self,models: list[MyModel]):
        for model in models:
            # 这里我们把 loaded 字段当作是否写入 DB 的标志（如果已 True 则跳过）
            print("load 执行 for",await model.user_id)
            model.loaded = True
            print("Loaded:",await model.modified)
        return models
    async def run(self,entry,*args):
        return await self.pipeline.run(entry,*args)

# # 把模块级被装饰的函数全部注册到 pipeline（把 globals() 传进去）
# pipeline.register_from_module(globals())
async def main():
    pipeline = ExamplePipeline()
    final_list = await pipeline.run("entry_1", "token-42")
    for final in final_list:
        print("最终 model:", final)
        print("user_id:", await final.user_id, "loaded:",await final.loaded,'is_called',await final.is_called)

# 调用 pipeline
if __name__ == "__main__":
  asyncio.run(main())
