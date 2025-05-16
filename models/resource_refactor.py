import enum
from typing import Optional, List
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


# 重新定义硬编码的资源分类
class Status(str, enum.Enum):
    DOWNLOADING = "正在下载"
    WAIT_Edit = "等待编辑"
    WAIT_UPLOAD = "等待上传"
    FINISH = '完成'
class ResourceEdit(SQLModel, table=True):
    """ 定义资源数据模型 """
    __tablename__ = "resource_edit"

    id: Optional[int] = Field(default=None, primary_key=True)
    full_path: str = Field(index=True, description="资源标题")
    download_task: Optional[str] = Field(default=None, description='子标题')
    description: Optional[str] = Field(default=None, description="资源描述")
    # 使用更新后的 ResourceCategory 枚举类型
    # 考虑是否需要更改默认值，如果 OTHER 不再合适
    category: ResourceCategory = Field(default=ResourceCategory.OTHER, description="资源分类")
    storage_path: str = Field(description="资源存储路径")
    total_episodes: Optional[str] = Field(default=None, description="总集数")
    updated_episodes: Optional[str] = Field(default=None, description="已更新的集数")
    image_path: Optional[str] = Field(default=None, description="封面图片路径")
    tags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON), description="标签列表")
    has_detect_risk: Optional[bool] = Field(default=False, description='判断是否已检查风险')
    risk_file: Optional[List[str]] = Field(default=None, sa_column=Column(JSON), description='被标记为风险的文件')
# 这个文件只包含 Resource 模型和相关的 Enum 定义


