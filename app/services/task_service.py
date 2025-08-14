# app/application/task_service.py

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

from app.application.use_case_1 import UseCase1
from app.domain.models.tasks import TaskPriority, Task, TaskType, TaskStatus


from app.infrastructure.persistence.repositories.task_repository import TaskRepository

# 配置日志
logger = logging.getLogger()


class TaskService:
    """
    任务应用服务

    封装了所有与任务相关的业务操作。
    通过构造函数注入一个实现了 TaskRepository 接口的实例，实现了依赖倒置。
    """

    def __init__(self, repository: TaskRepository,use_case:UseCase1):
        print('初始化成')
        """
        初始化 TaskService。

        :param repository: 一个任务仓库的实例，用于数据持久化。
        """
        self.repository = repository
        # 这个字典用于跟踪正在运行的 asyncio.Task 对象，以便可以取消它们
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.use_case = use_case
    def create_new_task(self, task_type: TaskType, priority: TaskPriority, parameters: Dict[str, Any],
                        **kwargs) -> Task:
        """
        创建一个新的任务实体并将其持久化。

        :param task_type: 任务的类型。
        :param priority: 任务的优先级。
        :param parameters: 任务执行所需的参数。
        :param kwargs: 其他任务属性，如 callback_url。
        :return: 创建并已保存的 Task 领域对象。
        """
        logger.info(f"服务层：正在创建类型为 '{task_type.value}' 的新任务。")
        # 1. 使用领域模型创建任务实例
        new_task = Task(
            task_type=task_type,
            priority=priority,
            parameters=parameters,
            **kwargs
        )

        # 2. 通过仓库接口将任务数据持久化
        # 我们传递字典，因为仓库处理的是原始数据结构
        self.repository.add(new_task.dict(by_alias=True))

        logger.info(f"任务 {new_task.id} 已成功创建并存入仓库。")
        return new_task

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        根据ID获取任务。

        :param task_id: 任务的唯一ID。
        :return: 如果找到，返回 Task 领域对象；否则返回 None。
        """
        task_data = self.repository.get_by_id(task_id)
        # 如果从仓库中获取到数据，则将其转换为 Task 领域对象
        return Task(**task_data) if task_data else None

    def get_all_tasks(self, status_filter: Optional[TaskStatus], page: int, limit: int) -> Tuple[List[Task], int]:
        """
        获取任务列表，支持过滤和分页。

        :param status_filter: 按状态筛选。
        :param page: 页码。
        :param limit: 每页数量。
        :return: 一个元组，包含任务对象列表和任务总数。
        """
        all_tasks_data = self.repository.get_all()

        # 应用筛选逻辑
        if status_filter:
            all_tasks_data = [t for t in all_tasks_data if t["status"] == status_filter.value]

        # 按创建时间倒序排列
        all_tasks_data.sort(key=lambda x: x["created_at"], reverse=True)

        total = len(all_tasks_data)

        # 应用分页逻辑
        start = (page - 1) * limit
        end = start + limit
        paginated_data = all_tasks_data[start:end]

        # 将字典数据转换为Task领域对象列表
        return [Task(**data) for data in paginated_data], total

    async def cancel_task(self, task_id: str) -> Optional[Task]:
        """
        取消一个任务。

        :param task_id: 要取消的任务ID。
        :return: 更新后的 Task 对象，如果任务不存在则返回 None。
        """
        task = self.get_task_by_id(task_id)
        if not task:
            return None

        # 检查任务是否可以被取消
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            raise ValueError(f"任务已结束（状态为 {task.status.value}），无法取消。")

        # 如果任务正在运行，取消其 asyncio.Task
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            logger.info(f"已发送取消信号给正在运行的任务 {task_id}。")

        # 无论是否在运行，都立即更新数据库中的状态
        task.cancel()
        self.repository.update(task_id, {"status": task.status, "completed_at": task.completed_at})

        return task

    def delete_task(self, task_id: str) -> bool:
        """
        删除一个任务。

        :param task_id: 要删除的任务ID。
        :return: 如果删除成功返回 True。
        :raises ValueError: 如果尝试删除一个正在进行的任务。
        """
        task = self.get_task_by_id(task_id)
        if not task:
            return False

        if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            raise ValueError("无法删除正在进行的任务，请先取消。")

        return self.repository.delete(task_id)

    async def run_task_in_background(self, task_id: str):
        """
        在后台执行指定任务的核心逻辑。
        这是一个调度器，会根据任务类型调用具体的执行函数。

        :param task_id: 要执行的任务ID。
        """
        task = self.get_task_by_id(task_id)
        if not task or task.status != TaskStatus.PENDING:
            logger.warning(f"任务 {task_id} 不存在或状态不为 PENDING，无法执行。")
            return

        # 将 asyncio.Task 对象存入字典，以便后续可以取消它
        asyncio_task = asyncio.current_task()
        self.running_tasks[task_id] = asyncio_task

        # 更新任务状态为“运行中”
        try:
            task.start()
            self.repository.update(task_id, {"status": task.status, "started_at": task.started_at})

            logger.info(f"开始执行任务 {task_id}，类型: {task.task_type}")

            # --- 任务执行逻辑分发 ---
            # 根据任务类型选择不同的执行器
            if task.task_type == TaskType.DATA_EXPORT:
                result = await self._execute_data_export(task)
            elif task.task_type == TaskType.FILE_PROCESSING:
                result = await self._execute_file_processing(task)
            elif task.task_type==TaskType.SYNC_CLOUD:
                result=await self._sync_cloud(task)
            elif task.task_type==TaskType.SYNC_TOP_METADATA:
                result=await self._sync_top_meta_data(task)
            else:
                # 默认或未知的任务类型处理
                await asyncio.sleep(5)
                result = {"message": "默认任务执行成功"}

            task.complete(result_data=result)
            logger.info(f"任务 {task_id} 成功完成。")

        except asyncio.CancelledError:
            # 当 .cancel() 被调用时会触发此异常
            task.cancel()
            logger.warning(f"任务 {task_id} 已被取消。")
            # 异常被捕获，不会传播

        except Exception as e:
            # 捕获执行过程中的任何其他异常
            error_message = f"{type(e).__name__}: {e}"
            task.fail(error_message=error_message)
            logger.error(f"任务 {task_id} 执行失败: {error_message}", exc_info=True)

        finally:
            # 无论成功、失败还是取消，都将最终状态持久化
            self.repository.update(task_id,
                                   task.dict(include={'status', 'completed_at', 'result', 'error', 'progress'}))
            # 从正在运行的任务列表中移除
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

    # --- 私有的任务执行器方法 ---

    async def _update_progress(self, task_id: str, progress: int):
        """辅助方法：更新任务进度并持久化。"""
        self.repository.update(task_id, {"progress": progress})

    async def _execute_data_export(self, task: Task) -> Dict[str, Any]:
        """模拟数据导出任务的具体实现。"""
        logger.info(f"执行数据导出: {task.id}, 参数: {task.parameters}")
        for p in range(0, 101, 20):
            await self._update_progress(task.id, p)
            await asyncio.sleep(2)  # 模拟工作负载
        return {
            "exported_records": task.parameters.get("record_count", 1000),
            "file_path": f"/exports/{task.id}.csv"
        }

    async def _execute_file_processing(self, task: Task) -> Dict[str, Any]:
        """模拟文件处理任务的具体实现。"""
        logger.info(f"执行文件处理: {task.id}, 参数: {task.parameters}")
        total_files = task.parameters.get("file_count", 5)
        for i in range(total_files):
            progress = int(((i + 1) / total_files) * 100)
            await self._update_progress(task.id, progress)
            await asyncio.sleep(3)  # 模拟处理每个文件
        return {
            "processed_files": total_files,
            "output_dir": f"/processed/{task.id}/"
        }

    async def _sync_cloud(self, task: Task) -> Dict[str, Any]:
        """
        执行云盘同步任务。
        它会从任务对象中解析参数，并使用多重分发调用相应的 `sync_cloud_disk` 方法。

        :param task: 包含执行参数的任务对象。
        :return: 包含操作结果的字典。
        """
        use_case1=self.use_case
        logger.info(f"开始执行 _sync_cloud 逻辑，任务ID: {task.id}")
        params = task.parameters
        if not params:
            raise ValueError("云盘同步任务(SYNC_CLOUD)缺少参数。")

        name_types = params.get("name_types")
        if not name_types or not isinstance(name_types, list):
            raise ValueError("参数 'name_types' 缺失或格式不正确。")

        # 根据其他可用参数进行分发
        if "titles" in params:
            titles = params["titles"]
            await use_case1.sync_cloud_disk(name_types, titles)
            return {"status": "完成", "synced_titles": [titles], }

        elif "tv_cate" in params:
            tv_cate= params["tv_cate"]
            # 一个好的实践是在任务参数中传递ID，而不是完整的对象。
            # 我们在这里根据ID获取完整的对象。

            await use_case1.sync_cloud_disk(name_types, tv_cate)
            return {"status": "完成", "synced_category": tv_cate}

        else:
            raise ValueError("云盘同步任务参数无效。必须包含 'titles' 或 'tv_cate'。")

    async def _sync_top_meta_data(self,task:Task) -> Dict[str, Any]:
        """
        执行top榜更新。


        :param task: 包含执行参数的任务对象。
        :return: 包含操作结果的字典。
        """
        use_case1 = self.use_case
        logger.info(f"开始执行 _sync_top_meta_data 逻辑，任务ID: {task.id}")
        params = task.parameters
        if not params:
            raise ValueError("top榜同步任务(SYNC_CLOUD)缺少参数。")



        if "tv_cate" in params and "count" in params:
            tv_cate = params["tv_cate"]
            count = params["count"]
            # 一个好的实践是在任务参数中传递ID，而不是完整的对象。
            # 我们在这里根据ID获取完整的对象。

            await use_case1.sync_top_meta_data(tv_cate, count)
            return {"status": "完成", "synced_category": tv_cate}

        else:
            raise ValueError("top榜同步任务参数无效。必须包含 'count' 和 'tv_cate'。")



#

