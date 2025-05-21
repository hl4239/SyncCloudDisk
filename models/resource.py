import enum
from datetime import datetime, timezone
from typing import Optional, List, Any

from pydantic import validator, field_validator
from pydantic_core.core_schema import ValidationInfo, FieldValidationInfo
from sqlalchemy import Column, JSON, Text, event, inspect
from sqlalchemy.orm import validates, attributes
from sqlmodel import Field, SQLModel
from sqlmodel.main import FieldInfo

class ResourceCategory(str, enum.Enum):
    """
    资源分类枚举
    """
    HOT_CN_DRAMA = "热门-国产剧"
    HOT_US_EU_DRAMA = "热门-欧美剧"
    HOT_JP_DRAMA = "热门-日剧"
    HOT_KR_DRAMA = "热门-韩剧"
    HOT_ANIME = "热门-动画"
    OTHER = "其他"


class Resource(SQLModel, table=True):
    """
    资源数据模型
    """
    __tablename__ = "resources"

    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="资源唯一ID"
    )

    title: str = Field(
        index=True,
        description="资源标题",
        max_length=255
    )

    subtitle: Optional[str] = Field(
        default=None,
        description="资源副标题",
        max_length=255
    )

    description: Optional[str] = Field(
        default=None,
        sa_type=Text,
        description="资源详细描述"
    )

    category: ResourceCategory = Field(
        default=ResourceCategory.OTHER,
        description="资源分类"
    )

    storage_path: str = Field(
        description="资源存储路径",
        max_length=512
    )
    cloud_storage_path: str = Field(
        description="资源存储路径",
        max_length=512
    )

    total_episodes: Optional[str] = Field(
        default=None,
        description="资源总集数",
        max_length=500
    )

    douban_last_episode_update:Optional[datetime] = Field(default=None)

    douban_last_async:Optional[datetime] = Field(default=None)

    cloud_disk_async_info:Optional[str] = Field(
        default=None,
        sa_column=Column(JSON),
        description="网盘同步更新的信息"
    )



    image_path: Optional[str] = Field(
        default=None,
        description="封面图片路径",
        max_length=512
    )

    tags: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="资源标签列表"
    )

    has_detect_risk: bool = Field(
        default=False,
        description="是否检测到风险内容"
    )

    risk_file: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="风险文件列表"
    )

    risk_file_handle: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="风险文件处理状态"
    )
    share_handle:  Optional[str] = Field(
        default=None,
        sa_column=Column(JSON),
        description="分享创建处理"
    )





