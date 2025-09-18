from datetime import time, datetime, date, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional,  Union

import pydantic
from beanie import Document, Indexed
from pydantic import Field, model_validator, BaseModel, field_validator, computed_field, field_serializer

from app.core.config import settings
from app.utils.date_to_weekday import weekday_cn


# --- 数据模型定义 ---

class MovieType(str, Enum):
    TV = "TV"
    MOVIE = "Movie"
    OTHER = "Other"

class CloudType(str, Enum):
    QUARK = "Quark"
    BAIDU="Baidu"
    UNKNOWN="Unknown"
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
class EpisodesInfo(pydantic.BaseModel):
    episode_number: int
    # TMDB 原始数据
    air_date: Optional[date] = None  # 只有年月日
    # 用户补充的数据 - 改为存储字符串格式
    air_time: Optional[str] = Field(default=None, description="用户补充的时间（ISO格式字符串，如 '20:00:00'）")
    tz_offset: int = Field(default=8)  # 时区偏移（默认北京时间 +8）

    # 自定义验证器处理 time 对象输入
    @field_validator('air_time', mode='before')
    @classmethod
    def validate_air_time(cls, value):
        """处理各种时间输入格式"""
        if value is None:
            return None
        if isinstance(value, time):
            # 将 time 对象转换为 ISO 格式字符串
            return value.isoformat()
        if isinstance(value, str):
            # 验证字符串格式是否正确
            try:
                time.fromisoformat(value)
                return value
            except ValueError:
                raise ValueError(f"无效的时间格式: {value}, 应该使用 ISO 格式如 '20:00:00'")
        raise ValueError(f"air_time 只支持 time 对象或 ISO 格式字符串，得到: {type(value)}")

    @property
    def air_time_obj(self) -> Optional[time]:
        """获取 time 对象"""
        if self.air_time is None:
            return None
        return time.fromisoformat(self.air_time)

    @computed_field
    @property
    def full_air_datetime(self) -> Optional[datetime]:
        """
        如果有 air_date，则返回合成的完整 datetime；
        如果 air_date 为 None，则返回 None；
        如果 air_time 为 None，则默认为 00:00（午夜）。
        tz_offset 用于构造时区偏移（默认 +8 小时）。
        """
        if self.air_date is None:
            return None
        # 如果没有提供 air_time，默认 00:00
        air_time_obj = self.air_time_obj or time(0, 0)
        tzinfo = timezone(timedelta(hours=self.tz_offset))
        return datetime.combine(self.air_date, air_time_obj, tzinfo=tzinfo)

    @computed_field
    @property
    def weekday(self) -> Optional[str]:
        if self.air_date:
            return weekday_cn(self.air_date)
        return None

    # 为了方便使用，添加一个设置时间的方法
    def set_air_time(self, time_obj: time):
        """设置播出时间"""
        self.air_time = time_obj.isoformat()

class TMDBInfos(pydantic.BaseModel):
    id:Optional[int]=Field(default=None)
    season_number:Optional[int]=Field(default=None)

    not_ensure:bool=Field(default=False,description='抓取结果不确定，需要人工抓取')
class CloudShareLink(BaseModel):
    """
    用于在链接爬虫模块内部表示一个被抓取到的网盘资源链接。
    这是一个非持久化模型 (DTO - Data Transfer Object)。
    """

    # 核心信息
    url: str = Field(..., description="资源的分享链接")
    title: Optional[str] = Field(default=None, description="从分享页面或帖子中提取的原始标题")
    share_password: Optional[str] = Field(None, description="分享密码（如果有）")

    @computed_field
    @property
    def type(self) -> CloudType:
        if 'quark' in self.url:
            return CloudType.QUARK
        return CloudType.UNKNOWN
class Movie(Document):
    # 1. 首先，定义 unique_key 字段
    douban_id: Indexed(str, unique=True) = Field(
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
    cloud_infos: Optional[list[MovieCloudInfo]] = Field(default=None, description='网盘信息')
    tmdb_infos:Optional[TMDBInfos]=Field(default=None)
    have_newer_episodes:bool=Field(default=False)
    episodes_info:Optional[list[EpisodesInfo]]=Field(default=None,description='剧集信息')


    @computed_field
    @property
    def is_finale(self)->bool:
        from app.services.movie_service import movie_service

        return movie_service.is_finale(self.episodes_info)

    def generate_path(self, ):
        return Path(settings.CLOUD_ROOT) / self.movie_type.value /  self.category /  self.year /  self.title_season

    def get_season_number(self):
        return self.tmdb_infos.season_number

    @computed_field
    @property
    def get_latest_episode_info(self)->Optional[EpisodesInfo]:
        """
        从列表中挑选已播出的最新剧集
        - 条件：full_air_datetime < now
        - 返回：episode_number 最大的 EpisodesInfo
        """
        episodes=self.episodes_info
        if not episodes:
            return None

        # 当前时间 (北京时间)
        tz_beijing = timezone(timedelta(hours=8))
        now = datetime.now(tz_beijing)

            # 筛选出已播出的剧集
        aired = [ep for ep in episodes if ep.full_air_datetime and ep.full_air_datetime < now]

        if not aired:
            return None

        # 返回 episode_number 最大的
        return max(aired, key=lambda ep: ep.episode_number)







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


