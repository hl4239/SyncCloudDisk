# -*- coding: utf-8 -*-
"""
领域模型模块

该模块定义了任务(Task)相关的核心业务实体、值对象和枚举。
这些模型是整个应用的基础，不依赖于任何外部框架或技术。
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid


class TaskStatus(str, Enum):
    """
    任务的执行状态枚举

    定义了一个任务在其生命周期中可能处于的所有状态。
    继承自 str 和 Enum，使其在 FastAPI 中能被正确序列化和文档化。
    """
    PENDING = "pending"  # 等待中：任务已创建，但尚未开始执行
    RUNNING = "running"  # 执行中：任务正在被处理
    COMPLETED = "completed"  # 已完成：任务成功执行完毕
    FAILED = "failed"  # 已失败：任务在执行过程中发生错误
    CANCELLED = "cancelled"  # 已取消：任务在执行前或执行中被用户手动取消


class TaskType(str, Enum):
    """
    任务类型的枚举

    定义了系统支持的各种后台任务类型。
    便于任务调度和执行逻辑的分发。
    """
    DATA_EXPORT = "data_export"  # 数据导出
    FILE_PROCESSING = "file_processing"  # 文件处理
    EMAIL_SENDING = "email_sending"  # 邮件发送
    REPORT_GENERATION = "report_generation"  # 报告生成
    DATA_MIGRATION = "data_migration"  # 数据迁移
    SYNC_CLOUD = "sync_cloud"
    SYNC_TOP_METADATA = "sync_top_metadata"


class TaskPriority(str, Enum):
    """
    任务优先级的枚举

    用于任务调度，决定任务执行的先后顺序。
    """
    LOW = "low"  # 低
    NORMAL = "normal"  # 普通
    HIGH = "high"  # 高
    URGENT = "urgent"  # 紧急


class Task(BaseModel):
    """
    任务领域实体 (Domain Entity)

    这是任务的核心数据结构，代表一个完整的任务对象。
    它聚合了任务的所有属性，并可以包含一些不涉及外部依赖的核心业务逻辑。
    使用 Pydantic BaseModel 有助于类型检查和数据验证。
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="任务的唯一标识符")
    task_type: TaskType = Field(..., description="任务类型")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="当前任务状态")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="任务优先级")

    parameters: Dict[str, Any] = Field(default_factory=dict, description="任务执行所需的参数")
    result: Optional[Dict[str, Any]] = Field(None, description="任务成功执行后的结果数据")
    error: Optional[str] = Field(None, description="任务失败时的错误信息")

    progress: int = Field(default=0, ge=0, le=100, description="任务执行进度（百分比）")

    created_at: datetime = Field(default_factory=datetime.now, description="任务创建时间")
    started_at: Optional[datetime] = Field(None, description="任务开始执行时间")
    completed_at: Optional[datetime] = Field(None, description="任务完成（成功、失败或取消）时间")

    # 额外元数据
    callback_url: Optional[str] = Field(None, description="任务完成后用于回调通知的URL")
    timeout: int = Field(default=300, description="任务执行的超时时间（秒）")
    estimated_duration: Optional[int] = Field(None, description="预估的任务执行时长（秒）")

    class Config:
        """Pydantic 模型配置"""
        use_enum_values = True  # 在序列化时使用枚举的值，而不是枚举成员本身

    def start(self):
        """将任务标记为开始执行"""
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.RUNNING
            self.started_at = datetime.now()
        else:
            # 可以选择抛出异常或记录警告
            raise ValueError(f"任务状态为 {self.status}，无法开始执行。")

    def complete(self, result_data: Dict[str, Any]):
        """将任务标记为成功完成"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.progress = 100
        self.result = result_data

    def fail(self, error_message: str):
        """将任务标记为失败"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error_message

    def cancel(self):
        """将任务标记为已取消"""
        if self.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            self.status = TaskStatus.CANCELLED
            self.completed_at = datetime.now()
        else:
            raise ValueError(f"任务已结束（状态为 {self.status}），无法取消。")