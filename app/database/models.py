import logging
import re
import uuid
from datetime import time, datetime, date, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional,  Dict, Any, Annotated

import pydantic
import pytz
from pydantic import Field, model_validator, BaseModel, field_validator, computed_field

from app.core.config import settings
from app.utils.date_to_weekday import weekday_cn
from app.utils.generic_crud import Filter
from beanie import Document, Indexed

from app.utils.obfuscate import obfuscate_title_pro

logger = logging.getLogger(__name__)


# --- 数据模型定义 ---

class MovieType(str, Enum):
    TV = "TV"
    MOVIE = "Movie"
    OTHER = "Other"

class CloudType(str, Enum):
    QUARK = "Quark"
    BAIDU="Baidu"
    UNKNOWN="Unknown"
    @staticmethod
    def get_link_type(link_str:str):
        if 'quark' in link_str:
            return CloudType.QUARK
        return CloudType.UNKNOWN

class PanCloud(Document):
    name: Optional[str] = Indexed(
        str, default=None, unique=True, description="唯一标识，创建时由用户手动输入"
    )

    cloud_type:Optional[CloudType] = Field(None,description='网盘类型')
    cookie: Optional[str] = Field(default=None, description="登录cookie")
    enable: bool = Field(default=False, description="是否启用该网盘")



class MovieCloudInfo(pydantic.BaseModel):
    pancloud_name:Optional[str]=Field(default=None, description="PanCloud name")
    last_save_time:Optional[datetime]=Field(None)
    last_save_link:Optional[str]=Field(None)
    last_save_success:bool=Field(default=False)
    cloud_path:Optional[str]=Field(default=None,)
    latest_episode_number:Optional[int]=Field(default=None)
    share_link:Optional[str]=Field(default=None)
    is_risk_share:bool=Field(default=False)
    save_suffixes:Optional[List[str]]=Field(default=[
            "mkv", "mp4", "avi", "mov", "m4v", "wmv", "flv",
            "torrent", "srt", "ass", "sub", "mp3", "aac", "zip"
        ],
    description='转存时只收录列出的文件格式')

    @model_validator(mode='after')
    def convert_datetimes(self):
        """在模型验证后转换时间字段"""
        if self.last_save_time:
            if self.last_save_time.tzinfo is None:
                self.last_save_time = self.last_save_time.replace(tzinfo=timezone.utc)
            self.last_save_time = self.last_save_time.astimezone(pytz.timezone("Asia/Shanghai"))
        return self
class MovieCategory(str, Enum):
    CHINA="China"
    JAPAN="Japan"
    KOREA="Korea"
    EUROPE="Europe"
    ANIMATION="Animation"
    OTHER="Other"


class EpisodesInfo(pydantic.BaseModel):
    episode_number: int
    # TMDB 原始数据
    air_date: Optional[date] = None  # 只有年月日
    # 用户补充的数据 - 改为存储字符串格式
    air_time: Optional[str] = Field(default=None, description="用户补充的时间（ISO格式字符串，如 '20:00:00'）")
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
        """
        if self.air_date is None:
            return None
        # 如果没有提供 air_time，默认 00:00
        air_time_obj = self.air_time_obj or time(0, 0)
        tzinfo = pytz.timezone("Asia/Shanghai")
        r=datetime.combine(self.air_date, air_time_obj, tzinfo=tzinfo)
        return  r

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
    id:Annotated[Optional[int], Filter(ops=["exists"])]=Field(default=None)
    season_number:Annotated[Optional[int], Filter(ops=["exists"])]=Field(default=None)

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
        if 'baidu' in self.url:
            return CloudType.BAIDU
        return CloudType.UNKNOWN
        # 初始化后自动从URL中提取密码

    @model_validator(mode="before")
    @classmethod
    def extract_password(cls, values):
        url = values.get("url", "")
        share_password = values.get("share_password")

        # 只在未提供 share_password 时尝试提取
        if not share_password and url:
            # 常见格式示例：
            # https://pan.baidu.com/s/xxxx?pwd=abcd
            # https://pan.baidu.com/s/xxxx 密码:abcd
            # https://pan.quark.cn/s/xxxx?pwd=1234
            match = re.search(r"(?:pwd|密码|提取码)[=:： ]?([A-Za-z0-9]{3,6})", url)
            if match:
                values["share_password"] = match.group(1)

        return values




class MetaDataProviderEnum (str, Enum):
    RENREN = "人人视频"

class MetaDataProvider(BaseModel):
    provider: MetaDataProviderEnum=Field(default=None)
    title: Optional[str] = Field(default=None)
    id:Optional[str]=Field(default=None)
    year:Optional[str]=Field(default=None)
    movie_type:Optional[MovieType]=Field(default=None)

class PlatformEnum(str, Enum):
    TG="Telegram"

class PlatformInfo(BaseModel):
    account:Optional[str]=Field(default=None)
    platform:Optional[str]=Field(default=None)
    channel_name:Optional[str]=Field(default=None)
    enable:bool=Field(default=True)


class PublishToPlatformInfo(BaseModel):
    publish_time:Optional[datetime]=Field(default=None)
    message_id:Optional[str]=Field(default=None)
    account:Optional[str]=Field(default=None)
    platform:Optional[PlatformEnum]=Field(default=None)
    episode_number:Optional[int]=Field(default=None)
    success:bool=Field(default=False)

    @model_validator(mode='after')
    def convert_datetimes(self):
        """在模型验证后转换时间字段"""
        if self.publish_time:
            if self.publish_time.tzinfo is None:
                self.publish_time = self.publish_time.replace(tzinfo=timezone.utc)
            self.publish_time = self.publish_time.astimezone(pytz.timezone("Asia/Shanghai"))
        return self


class Movie(Document):
    # 1. 首先，定义 unique_key 字段
    douban_id: Indexed(str, unique=True) = Field(
        description="豆瓣影视id"
    )
    title: Optional[str] = Field(default=None)
    title_season:Annotated[str, Filter(ops=["contains"])] = Field(description='title和season一起')
    original_title_season:Optional[str]=Field(default=None,description='原名，比如tmdb中可能只能用韩剧的韩语原名在哪查询到')
    original_title:Optional[str]=Field(default=None,description='原始名的标题，不含季')
    subtitle: Optional[list[str]] = Field(default=None, description='子标题')
    actors:Optional[List[str]]=Field(default_factory=list,description='演员、配音')
    aliases:Optional[List[str]]=Field(default_factory=list,description='别名')
    genres:Optional[List[str]]=Field(default_factory=list,description='影视风格')

    pic:Optional[str] = Field(default=None,description='图片地址')
    description: Annotated[str, Filter(ops=["contains"])]= Field(default=None)
    year: Annotated[str, Filter(ops=["eq"])]=Field(default=None)
    category:Annotated[MovieCategory,Filter(ops=["eq"])] =Field(default=None)
    movie_type: Annotated[ MovieType,Filter(ops=["eq"])] = Field( description='影视类型电影或电视')
    season: Optional[str] = Field(default=None, description='描述影视第几季, e.g., "1", "第一季"')
    total_episodes:Optional[str]=Field(default=None,description='描述影视总剧集数')
    cloud_infos: Optional[list[MovieCloudInfo]] = Field(default_factory=list, description='网盘信息')
    tmdb_infos:Optional[TMDBInfos]=Field(default=None)
    episodes_info:Optional[list[EpisodesInfo]]=Field(default_factory=list,description='剧集信息')
    share_links:Optional[List[str]]=Field(default_factory=list,description='追踪的网盘分享链接')
    metadata_providers:Optional[List[MetaDataProvider]]=Field(default_factory=list,description='元数据提供者的信息')
    create_time:Annotated[Optional[datetime],Filter(ops=["eq","gt","lt"])] =Field(default=None,description='创建时间')
    update_time:Annotated[Optional[datetime],Filter(ops=["eq","gt","lt"])]=Field(default=None,description='更新时间')
    pubdate:Annotated[Optional[date],Filter(ops=["eq","gte","lte"])]=Field(default=None,description='更新时间')

    publish_to_platform_infos:Optional[List[PublishToPlatformInfo]]=Field(default_factory=list,description='发布至平台的信息')

    @model_validator(mode='after')
    def convert_datetimes(self):
        """在模型验证后转换时间字段"""
        if self.create_time:
            if self.create_time.tzinfo is None:
                self.create_time = self.create_time.replace(tzinfo=timezone.utc)
            self.create_time = self.create_time.astimezone(pytz.timezone("Asia/Shanghai"))

        if self.update_time:
            if self.update_time.tzinfo is None:
                self.update_time = self.update_time.replace(tzinfo=timezone.utc)
            self.update_time = self.update_time.astimezone(pytz.timezone("Asia/Shanghai"))


        return self

    def is_tmdb_infos_avaliable(self):
        return self.tmdb_infos is not None and self.tmdb_infos.id is not None and self.tmdb_infos.season_number is not None

    def generate_path(self, is_obfuscate=False):
        try:

            print(self.title_season)
            if is_obfuscate:
                title_season=obfuscate_title_pro(self.title_season, pinyin_ratio=0.3, decompose_ratio=0.3, keep_char_ratio=0.4,
                                               separator='-')
            else:
                title_season=self.title_season
        except Exception as e:
            logger.error(self.title_season, exc_info=True)
            raise e
        return  (Path(settings.CLOUD_ROOT) / self.movie_type.value /  self.category /  self.year /  title_season).as_posix()

    def get_season_number(self):
        return self.tmdb_infos.season_number

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
        now = datetime.now(pytz.timezone("Asia/Shanghai"))

            # 筛选出已播出的剧集
        aired = [ep for ep in episodes if ep.full_air_datetime and ep.full_air_datetime < now]

        if not aired:
            return None

        # 返回 episode_number 最大的
        return max(aired, key=lambda ep: ep.episode_number)

    def get_today_will_update_episodes(self):
        episodes=self.episodes_info
        if not episodes:
            return []
        now = datetime.now(pytz.timezone("Asia/Shanghai"))
        return [i for i in episodes if i.air_date==now.date()]

    def is_clouds_synced_latest(self):
        """
        所有网盘是否都更新到最新
        :return:
        """

        l_ei=self.get_latest_episode_info()
        if not l_ei:
            return False
        latest_episodes_number=l_ei.episode_number

        if not self.cloud_infos:
            return False
        for i in self.cloud_infos:
            if i.latest_episode_number is None or  i.latest_episode_number<latest_episodes_number:
                return False
        return True




class SplitTitleSeasonRegular(Document):
    regular:str
    description:str

class OpenAISource(Document):
    name:str
    key:str
    base_url:str
    models:List[str]=Field(default_factory=list)
    extra_body:Dict[str, Any]=Field(default={})
    # 关键配置，防list类型报错
    model_config = {
        "arbitrary_types_allowed": True
    }

# -------------------------
# Beanie Document (持久化模型)
# -------------------------
class CronJobDoc(Document):
    """
    使用 Beanie Document 持久化定时任务。
    - job_id: 业务上的唯一 id（字符串），保留用于查询/UI 操作。
    - created_at/last_run_at/next_run_at 使用 datetime（UTC）
    - params 存储为 dict
    """
    job_id: str = Field(default_factory=lambda: uuid.uuid4().hex, index=True)
    task_name: str
    cron: str
    params: Dict[str, Any] = Field(default_factory=dict)
    tz: str = "UTC"
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(pytz.timezone("Asia/Shanghai")))
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None

    @model_validator(mode='after')
    def convert_datetimes(self):
        """在模型验证后转换时间字段"""
        if self.created_at:
            if self.created_at.tzinfo is None:
                self.created_at = self.created_at.replace(tzinfo=timezone.utc)
            self.created_at = self.created_at.astimezone(pytz.timezone("Asia/Shanghai"))

        if self.last_run_at:
            if self.last_run_at.tzinfo is None:
                self.last_run_at = self.last_run_at.replace(tzinfo=timezone.utc)
            self.last_run_at = self.last_run_at.astimezone(pytz.timezone("Asia/Shanghai"))

        if self.next_run_at:
            if self.next_run_at.tzinfo is None:
                self.next_run_at = self.next_run_at.replace(tzinfo=timezone.utc)
            self.next_run_at = self.next_run_at.astimezone(pytz.timezone("Asia/Shanghai"))

        return self

    class Settings:
        name = "cron_jobs"  # Mongo collection name

class OpenAiConfig(BaseModel):
    default_source_name:Optional[str]=Field(default=None,description='')
    sources:List[OpenAISource]=Field(default_factory=list)

class SystemConfig(Document):
    # system 字段支持 eq 和 contains 查询
    system: str = Field(default='影视管理系统', description="系统名称或标识")

    # version 字段只支持 eq 查询
    version: str= Field(default='1.0',description='版本号')

    open_ai_config:OpenAiConfig=Field(default=OpenAiConfig())

    split_title_season_patterns:List[SplitTitleSeasonRegular]=Field(default_factory=list)

    platform_infos:Optional[List[PlatformInfo]] = Field(default_factory=list)


    class Settings:
        name = "system_config"



