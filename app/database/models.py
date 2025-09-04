import re
from enum import Enum
from pathlib import Path
from typing import List, Optional, Any, Union
from datetime import datetime

import pydantic
from beanie import Document, Indexed
from pydantic import Field, model_validator, BaseModel

from app.core.config import settings


# --- 数据模型定义 ---

class MovieType(str, Enum):
    TV = "TV"
    MOVIE = "Movie"
    OTHER = "Other"

class CloudType(str, Enum):
    QUARK = "Quark"
    BAIDU="Baidu"
class PanCloud(Document):


    phone_tail:str=Field(default=None,description='手机尾号后4位')
    cloud_type:CloudType=Field(default=CloudType.QUARK)
    cookie:str=Field(default=None,description='登录cookie')
    unique_key: Optional[Indexed(str, unique=True)] = None
    @model_validator(mode="after")
    def generate_unique_key(self) -> 'PanCloud':
        """
        在模型初始化并填充默认值后，生成 unique_key。
        """
        # 检查 unique_key 是否已经被赋值，如果没有，则生成它
        if not self.unique_key:
            # 此处可以直接访问 self 的属性，它们已经包含了用户输入或字段的默认值
            # 例如，如果创建实例时未提供 season，self.season 的值会是 "第一季"

            self.unique_key = f"{self.cloud_type.value}_{self.phone_tail}"

        # 'after' 模式的验证器必须返回模型实例 self
        return self
class MovieCloudInfo(pydantic.BaseModel):
    cloud_type: Optional[CloudType]=Field(default=None,description='网盘类型')
    cloud_unique_key:Optional[PanCloud]=None
    path:Optional[Path]=None


class TVCategory(str, Enum):
    CHINA="China"
    JAPAN="Japan"
    KOREA="Korea"
    EUROPE="Europe"
    ANIMATION="Animation"
    OTHER="Other"
class MovieCategory(str, Enum):
    ALL="All"
class MovieStatus(Enum):
    UPCOMING = "upcoming"  # 未开播
    ONGOING = "ongoing"  # 更新中
    FINISHED = "finished"  # 已完结

class TMDBInfos(pydantic.BaseModel):
    id:Optional[str]=Field(default=None)

class Movie(Document):
    # 1. 首先，定义 unique_key 字段
    douban_id: Optional[Indexed(str, unique=True)] = Field(
default=None,
        description="豆瓣影视id"
    )
    title: Optional[str] = Field(default=None)
    title_season:str = Field(description='title和season一起')
    subtitle: Optional[list[str]] = Field(default=None, description='子标题')
    description: Optional[str] = Field(default=None)
    year: Optional[str]=Field(default=None)
    category: Union[TVCategory, MovieCategory]=Field(default=None)
    movie_type: MovieType = Field( description='影视类型电影或电视')
    season: Optional[str] = Field(default=None, description='描述影视第几季, e.g., "1", "第一季"')
    total_episodes:Optional[str]=Field(default=None)
    current_episodes:Optional[str]=Field(default=None)
    status:Optional[MovieStatus]=Field(default=None)
    cloud_infos: Optional[list[MovieCloudInfo]] = Field(default=None, description='网盘信息')
    tmdb_infos:Optional[TMDBInfos]=Field(default=None)
    @model_validator(mode="after")
    def generate_unique_key(self) -> 'Movie':
        """
        在模型初始化并填充默认值后，生成 unique_key。
        """
        # 检查 unique_key 是否已经被赋值，如果没有，则生成它
        if not self.unique_key:
            # 此处可以直接访问 self 的属性，它们已经包含了用户输入或字段的默认值
            # 例如，如果创建实例时未提供 season，self.season 的值会是 "第一季"
            year = self.year
            tv_type = self.movie_type.value
            title_season = self.title_season
            self.unique_key = f"{year}_{tv_type}_{title_season}"

        # 'after' 模式的验证器必须返回模型实例 self
        return self

    def generate_path(self, ):
        return Path(settings.CLOUD_ROOT) / self.movie_type.value /  self.category /  self.title /  self.title_season

class SplitTitleSeasonRegular(Document):
    regular:str
    description:str

class OpenAISource(Document):
    name:str
    key:str
    base_url:str
    models:List[str]
    # 关键配置，防list类型报错
    model_config = {
        "arbitrary_types_allowed": True
    }


