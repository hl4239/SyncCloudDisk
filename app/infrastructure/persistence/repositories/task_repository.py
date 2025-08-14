# -*- coding: utf-8 -*-
"""
任务数据仓库模块

该模块负责任务数据的持久化和管理。
它将任务管理的具体实现（如内存、数据库、Redis等）与业务逻辑解耦。
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from app.domain.models.tasks import TaskStatus


# 从领域层导入核心模型
# 假设您的枚举类都放在了 app/domain/task_models.py 文件中


class TaskRepository(ABC):
    """
    任务仓库的抽象基类 (接口)

    定义了所有任务仓库实现都必须遵守的方法。
    这确保了无论底层存储技术如何变化，上层服务的调用方式都保持一致。
    """

    @abstractmethod
    def add(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加一个新任务到仓库。

        :param task_data: 包含任务所有初始信息的字典。
        :return: 已添加的任务字典。
        """
        pass

    @abstractmethod
    def get_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        根据任务ID获取任务详情。

        :param task_id: 任务的唯一标识符。
        :return: 如果找到，返回任务字典；否则返回 None。
        """
        pass

    @abstractmethod
    def get_all(self) -> List[Dict[str, Any]]:
        """
        获取仓库中所有的任务。

        :return: 包含所有任务字典的列表。
        """
        pass

    @abstractmethod
    def update(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        更新指定ID的任务信息。

        :param task_id: 要更新的任务ID。
        :param updates: 包含要更新的字段和新值的字典。
        :return: 更新后的任务字典；如果任务不存在则返回 None。
        """
        pass

    @abstractmethod
    def delete(self, task_id: str) -> bool:
        """
        从仓库中删除一个任务。

        :param task_id: 要删除的任务ID。
        :return: 如果删除成功返回 True，否则返回 False。
        """
        pass

    @abstractmethod
    def find_by_status(self, status: TaskStatus) -> List[Dict[str, Any]]:
        """
        根据状态查找任务。

        :param status: 要筛选的任务状态 (TaskStatus 枚举成员)。
        :return: 符合状态的任务列表。
        """
        pass


class InMemoryTaskRepository(TaskRepository):
    """
    一个基于内存的任务仓库实现。

    它将所有任务数据存储在内存的一个字典中。
    注意：服务重启后所有数据都会丢失。适用于开发、测试或简单场景。
    这个类在应用中通常以单例模式存在。
    """

    def __init__(self):
        """
        初始化任务存储。
        _tasks 是一个以 task_id 为键，任务字典为值的字典，作为内存数据库。
        """
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def add(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加一个新任务到内存中。"""
        task_id = task_data.get("id")
        if not task_id:
            raise ValueError("任务数据必须包含 'id' 字段")
        if task_id in self._tasks:
            raise ValueError(f"任务ID '{task_id}' 已存在")

        self._tasks[task_id] = task_data
        return task_data

    def get_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """根据ID从内存中获取任务。"""
        return self._tasks.get(task_id)

    def get_all(self) -> List[Dict[str, Any]]:
        """从内存中获取所有任务的列表。"""
        return list(self._tasks.values())

    def update(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """在内存中更新一个任务。"""
        task = self.get_by_id(task_id)
        if task:
            task.update(updates)
            return task
        return None

    def delete(self, task_id: str) -> bool:
        """从内存中删除一个任务。"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def find_by_status(self, status: TaskStatus) -> List[Dict[str, Any]]:
        """在内存中按状态筛选任务。"""
        return [task for task in self._tasks.values() if task.get("status") == status]

# --- 关于 `running_tasks` 的说明 ---
# 在原始代码中，`TaskManager` 还管理了一个 `running_tasks` 字典，
# 用于存放 `asyncio.Task` 对象以实现任务取消。
#
# 在分层架构中，这种运行时状态的管理通常属于“应用服务层(Application Service)”的职责，
# 而不是“仓库(Repository)”的职责。仓库应只关心数据的持久化状态。
#
# 因此，`running_tasks: Dict[str, asyncio.Task]` 这个字典
# 应该被移动到 `app/application/task_service.py` 中进行管理。