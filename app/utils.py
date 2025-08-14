import asyncio
import json
import logging
import sys
from typing import Type, Optional, List, Any, Dict, AsyncIterable, AsyncIterator, Union, Callable
from pydantic import BaseModel, Field
from sqlalchemy import TypeDecorator, JSON
from sqlalchemy.ext.mutable import MutableDict
import copy
import threading
from contextlib import contextmanager




import asyncio
from typing import Union, List, AsyncIterator

class SimpleMutablePydanticDict(MutableDict):
    """简化的可变Pydantic字典，支持直接访问模型属性"""

    def __init__(self, model_class: Type[BaseModel], data=None):
        self._model_class = model_class
        if data is None:
            data = {}

        # 创建模型实例
        try:
            if isinstance(data, BaseModel):
                self._model_instance = data
                data = data.dict()
            else:
                self._model_instance = model_class(**data)
                data = self._model_instance.dict()
        except Exception as e:
            print(f"模型创建失败: {e}")
            self._model_instance = model_class()
            data = self._model_instance.dict()

        super().__init__(data)

    def sync_from_model(self):
        """从模型实例同步数据到字典"""
        try:
            new_data = self._model_instance.dict()
            self.clear()
            self.update(new_data)
            self.changed()  # 标记SQLAlchemy变更
        except Exception as e:
            print(f"同步数据失败: {e}")

    def sync_to_model(self):
        """从字典同步数据到模型实例"""
        try:
            self._model_instance = self._model_class(**dict(self))
        except Exception as e:
            print(f"重建模型失败: {e}")

    def __getattr__(self, name):
        """代理属性访问到模型"""
        if name.startswith('_'):
            return super().__getattribute__(name)

        # 首先检查模型实例是否有该属性
        if hasattr(self._model_instance, name):
            return getattr(self._model_instance, name)

        # 然后检查字典中是否有该键
        if name in self:
            return self[name]

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        """代理属性设置到模型"""
        if name.startswith('_') or name in ('data',):
            super().__setattr__(name, value)
            return

        # 检查是否是模型字段
        if hasattr(self, '_model_class') and hasattr(self._model_class, '__fields__'):
            if name in self._model_class.__fields__:
                # 设置模型属性
                if hasattr(self, '_model_instance'):
                    setattr(self._model_instance, name, value)
                    # 同步到字典
                    self[name] = value
                    self.changed()
                return

        super().__setattr__(name, value)

    def __setitem__(self, key, value):
        """重写字典项设置"""
        super().__setitem__(key, value)
        self.changed()
        # 同步到模型
        self.sync_to_model()

    def update(self, *args, **kwargs):
        """重写更新方法"""
        super().update(*args, **kwargs)
        self.changed()
        # 同步到模型
        self.sync_to_model()

    def get_model_instance(self):
        """获取当前模型实例"""
        return self._model_instance

    @classmethod
    def coerce(cls, key, value):
        """SQLAlchemy调用的类型转换方法"""
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return value
        return super().coerce(key, value)


class SimplePydanticMutableJSON(TypeDecorator):
    """简化的Pydantic JSON字段"""
    impl = JSON
    cache_ok = True

    def __init__(self, model_class: Type[BaseModel], *args, **kwargs):
        self.model_class = model_class
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        """存储到数据库前的处理"""
        if value is None:
            return None

        if isinstance(value, SimpleMutablePydanticDict):
            model_instance = value.get_model_instance()
            if model_instance:
                return json.loads(model_instance.json())
            else:
                return dict(value)
        elif isinstance(value, BaseModel):
            return json.loads(value.json())
        elif isinstance(value, dict):
            return value
        return value

    def process_result_value(self, value, dialect):
        """从数据库加载后的处理"""
        if value is None:
            return SimpleMutablePydanticDict(self.model_class, {})
        return SimpleMutablePydanticDict(self.model_class, value)


def create_simple_mutable_pydantic_field(model_class: Type[BaseModel]):
    """创建简化的可变Pydantic字段"""

    class SpecificSimpleMutablePydanticDict(SimpleMutablePydanticDict):
        def __init__(self, data=None):
            super().__init__(model_class, data)

        @classmethod
        def coerce(cls, key, value):
            if isinstance(value, cls):
                return value
            if isinstance(value, dict):
                return cls(value)
            if isinstance(value, model_class):
                return cls(value.dict())
            return super().coerce(key, value)

    return SpecificSimpleMutablePydanticDict.as_mutable(SimplePydanticMutableJSON(model_class))

class AsyncCachedIterator:
    """
    一个异步迭代器包装器：
    - 第一次异步遍历会从源（列表或 async generator）读取并缓存
    - 后续所有异步遍历都会只从缓存中读取
    """
    def __init__(self, source: Union[List[str], AsyncIterator[str]]):
        self._source = source
        self._cache: List[str] = []
        self._is_consumed = False
        self._lock = asyncio.Lock()

    def __aiter__(self):
        return _CachedIteratorView(self)


class _CachedIteratorView:
    """每次 async for 返回独立视图，共享缓存，但有独立 index"""
    def __init__(self, parent: AsyncCachedIterator):
        self._parent = parent
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
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

            try:
                if isinstance(self._parent._source, AsyncIterator):
                    item = await anext(self._parent._source)
                else:
                    item = self._parent._source[len(self._parent._cache)]

                self._parent._cache.append(item)
                self._index += 1
                return item
            except (StopAsyncIteration, IndexError):
                self._parent._is_consumed = True
                raise StopAsyncIteration



