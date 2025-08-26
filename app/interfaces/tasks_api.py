# -*- coding: utf-8 -*-
"""
接口层 (Interfaces) / API 端点

该模块定义了所有与任务相关的HTTP API端点。
它使用FastAPI的APIRouter来组织路由，并依赖于应用服务层(TaskService)来处理业务逻辑。
它负责处理HTTP请求和响应的序列化/反序列化。
"""
from dependency_injector.wiring import inject, Provide
# -------------------- CHANGE 1: Import Query --------------------
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.domain.dtos.comm import ApiResponse
from app.domain.models.tasks import TaskType, TaskPriority, TaskStatus, Task
from app.infrastructure.containers import container, Container

from app.services.task_service import TaskService

logger = logging.getLogger()


# --- API 数据传输对象 (DTOs) / Schemas ---
# 这些Pydantic模型定义了API的输入(Request)和输出(Response)契约。

class TaskCreateRequest(BaseModel):
    """用于创建任务的请求体模型"""
    task_type: TaskType = Field(..., description="任务类型")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="任务优先级")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="任务执行所需的参数")
    callback_url: Optional[str] = Field(None, description="任务完成后用于回调通知的URL")


class TaskUpdateRequest(BaseModel):
    """用于更新任务的请求体模型（当前仅支持更新优先级）"""
    priority: Optional[TaskPriority] = None


class TaskResponse(BaseModel):
    """标准的任务信息响应模型"""
    id: str
    task_type: TaskType
    status: TaskStatus
    priority: TaskPriority
    progress: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # -------------------- CHANGE 2: Fix Pydantic V2 Warning --------------------
    class Config:
        from_attributes = True  # 允许模型从ORM对象（或类似对象）创建，这里用于从Task领域模型创建

    @classmethod
    def from_domain(cls, task: Task) -> "TaskResponse":
        """辅助方法：从Task领域模型创建TaskResponse实例"""
        return cls.model_validate(task) # .from_orm(task) is deprecated, model_validate is the new way





class TaskListResponse(ApiResponse):
    """任务列表的响应封装，包含分页信息"""
    data: List[TaskResponse]
    pagination: Dict[str, Any]


# --- API 路由定义 ---
router = APIRouter(
    prefix="/tasks",  # 所有该路由下的路径都会以 /tasks 开头
    tags=["Tasks Management"]  # 在Swagger UI中进行分组，方便查阅
)

@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED, summary="创建并启动一个新任务")
async def create_task_endpoint(
        task_data: TaskCreateRequest,
        background_tasks: BackgroundTasks,

):

    """
    创建一个新的后台任务。任务创建后会立即加入后台执行队列。
    - **task_type**: 任务的类型，例如 "data_export"。
    - **priority**: 任务的优先级。
    - **parameters**: 一个字典，包含执行该任务所需的具体参数。
    """
    task_service = container.task_service()
    try:
        # 调用应用服务创建任务
        task = task_service.create_new_task(
            task_type=task_data.task_type,
            priority=task_data.priority,
            parameters=task_data.parameters,
            callback_url=task_data.callback_url
        )
        # 使用FastAPI的后台任务机制来异步执行
        background_tasks.add_task(task_service.run_task_in_background, task.id)

        return ApiResponse(
            message="任务创建成功，正在后台执行",
            data=TaskResponse.from_domain(task)
        )
    except Exception as e:
        logger.error(f"创建任务时发生错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建任务失败: {e}"
        )

@inject
@router.get("", response_model=TaskListResponse, summary="获取任务列表")
# -------------------- CHANGE 3: Replace Field with Query --------------------
def get_tasks_endpoint(
        status_filter: Optional[TaskStatus] = Query(None, alias="status", description="按任务状态筛选"),
        page: int = Query(1, ge=1, description="页码"),
        limit: int = Query(10, ge=1, le=100, description="每页数量"),

):
    """
    获取任务列表，支持按状态筛选和分页。
    """
    task_service = container.task_service()
    tasks, total = task_service.get_all_tasks(status_filter=status_filter, page=page, limit=limit)

    return TaskListResponse(
        message="获取任务列表成功",
        data=[TaskResponse.from_domain(t) for t in tasks],
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if limit > 0 else 0
        }
    )

@inject
@router.get("/{task_id}", response_model=ApiResponse, summary="获取单个任务的详细信息")
def get_task_endpoint(
        task_id: str,

):
    """
    根据任务ID获取其当前状态、进度和结果。
    """
    task_service = container.task_service()
    task = task_service.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    return ApiResponse(
        message="获取任务信息成功",
        data=TaskResponse.from_domain(task)
    )

@inject
@router.post("/{task_id}/cancel", response_model=ApiResponse, summary="取消一个正在进行或等待中的任务")
async def cancel_task_endpoint(
        task_id: str,

):
    """
    取消一个任务。只能取消处于 PENDING 或 RUNNING 状态的任务。
    """
    task_service = container.task_service()
    try:
        updated_task = await task_service.cancel_task(task_id)
        if not updated_task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

        return ApiResponse(
            message="任务已成功取消",
            data=TaskResponse.from_domain(updated_task)
        )
    except ValueError as e:
        # 捕获服务层抛出的业务逻辑异常
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@inject
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除一个已完成的任务")
def delete_task_endpoint(
        task_id: str,

):
    """
    从系统中删除一个任务的记录。只能删除已完成 (COMPLETED)、失败 (FAILED) 或已取消 (CANCELLED) 的任务。
    """
    task_service=container.task_service()
    try:
        success = task_service.delete_task(task_id)
        if not success:
            # 如果服务层返回False，说明任务一开始就不存在
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
        # 成功删除，HTTP 204 不需要返回任何内容
        return None
    except ValueError as e:
        # 捕获尝试删除正在进行的任务时抛出的异常
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))