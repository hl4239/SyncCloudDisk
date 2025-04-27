import enum
from typing import Optional, List
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

# 重新定义硬编码的资源分类
class ResourceCategory(str, enum.Enum):
    HOT_CN_DRAMA = "热门-国产剧"
    HOT_US_EU_DRAMA = "热门-欧美剧"
    HOT_JP_DRAMA = "热门-日剧"
    HOT_KR_DRAMA = "热门-韩剧"
    HOT_ANIME = "热门-动画"
    # 可以考虑保留一个通用的 OTHER 或添加更多分类
    OTHER = "其他" # 保留一个默认/其他分类通常是好主意

class Resource(SQLModel, table=True):
    """ 定义资源数据模型 """
    __tablename__ = "resources"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, description="资源标题")
    subtitle:Optional[str]=Field(default=None, description='子标题')
    description: Optional[str] = Field(default=None, description="资源描述")
    # 使用更新后的 ResourceCategory 枚举类型
    # 考虑是否需要更改默认值，如果 OTHER 不再合适
    category: ResourceCategory = Field(default=ResourceCategory.OTHER, description="资源分类")
    storage_path: str = Field(description="资源存储路径")
    total_episodes: Optional[str] = Field(default=None, description="总集数")
    updated_episodes:Optional[str]  = Field(default=None, description="已更新的集数")
    image_path: Optional[str] = Field(default=None, description="封面图片路径")
    tags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON), description="标签列表")

# 这个文件只包含 Resource 模型和相关的 Enum 定义