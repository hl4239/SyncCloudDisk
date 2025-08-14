# app/domain/models/resource.py
import datetime
import enum
import re
from typing import Optional, List

from pydantic import BaseModel
from sqlalchemy.ext.mutable import MutableList
from sqlmodel import Field, SQLModel, Column, JSON, Text

from app.infrastructure.config import settings
from app.services.public_episode_normalize_service import PublicEpisodeNormalizeService
from app.utils import create_simple_mutable_pydantic_field


# --- Enums and Simple Data Classes ---
class TvCategory(str, enum.Enum):
    HOT_CN_DRAMA = "热门-国产剧"
    HOT_US_EU_DRAMA = "热门-欧美剧"
    HOT_JP_DRAMA = "热门-日剧"
    HOT_KR_DRAMA = "热门-韩剧"
    HOT_ANIME = "热门-动画"
    OTHER = "其他"



class Account(BaseModel):
    name:Optional[str]=None
    cloud_storage_path:Optional[str]=None
    create_share_link:Optional[str]=None
    last_sync_share_links:list[str]=Field(default=[])
    is_sync_finish:bool=Field(default=False,description='表示剧集信息已经更新到完结')

    def set_is_sync_finish(self,is_sync_finish:bool=False):
        self.is_sync_finish=is_sync_finish

    @classmethod
    def default_factory(cls, name:str=None, cloud_storage_path:str=None):
        return Account(name=name, cloud_storage_path=cloud_storage_path)

class EpisodesInfo(BaseModel):
    total_episodes:Optional[str]=Field(default=None)
    season:Optional[str]=Field(default=None)
    episodes_url:Optional[str]=Field(default=None)
    last_update_time:Optional[datetime.datetime]=Field(default=None,description='记录剧集信息发生更改的时间')

    def is_finished(self):
        if self.total_episodes is not None and '全' in self.total_episodes:
            return True
        return False


class CloudDiskInfo(BaseModel):
    last_sync_share_link: Optional[str] = None
    accounts:List[Account]= Field(default_factory=list)

class Resource(SQLModel, table=True):

    # Fields
    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = Field(default=None, index=True)
    subtitle: Optional[str] = None
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    tv_category: Optional[TvCategory] = Field(default=TvCategory.OTHER)

    image_path: Optional[str] = None
    tags: List[str] = Field(default_factory=list, sa_column=Column(MutableList.as_mutable(JSON))) # Ensure default_factory for lists
    last_metadata_update_time: Optional[datetime.datetime] = Field(default=None)
    episodes_info: Optional[EpisodesInfo] = Field(
        default=None,
        sa_column=Column(create_simple_mutable_pydantic_field(EpisodesInfo))
    )
    cloud_disk_info: CloudDiskInfo = Field(
        default_factory=CloudDiskInfo,
        sa_column=Column(create_simple_mutable_pydantic_field(CloudDiskInfo))
    )
    async def update_episode_info(self, episodes_info: EpisodesInfo):
        """
        对剧集信息更新，如果存在且更新则更新
        """
        exist_total_episode = self.episodes_info.total_episodes
        to_add_total_episodes = episodes_info.total_episodes
        # 如果都有值，且待添加的更新就更新
        if exist_total_episode is not None and exist_total_episode != '' and (to_add_total_episodes is not None and to_add_total_episodes != ''  ):
            episode_normalized_list = await PublicEpisodeNormalizeService.generate_name(
                [exist_total_episode, to_add_total_episodes])
            episode_normalized_maps = {
                i.original_name: i
                for i in episode_normalized_list
            }
            exist_normalized = episode_normalized_maps.get(exist_total_episode).normalized_name
            to_add_normalized = episode_normalized_maps.get(to_add_total_episodes).normalized_name
            exist_episode_num_list = PublicEpisodeNormalizeService.normalized_name_to_num_list(exist_normalized)
            to_add_episode_num_list = PublicEpisodeNormalizeService.normalized_name_to_num_list(to_add_normalized)
            if len(to_add_episode_num_list) > len(exist_episode_num_list):
                self.episodes_info.total_episodes = to_add_total_episodes
                self.episodes_info.last_update_time = datetime.datetime.now()


        elif (exist_total_episode is None or exist_total_episode == '') and (to_add_total_episodes is not None and to_add_total_episodes != ''):
            self.episodes_info = episodes_info

            self.episodes_info.last_update_time = datetime.datetime.now()

    def get_year(self):
        match = re.search(r'\(?(20\d{2})\)?', self.title)
        if match:
            return match.group(1)
        return None

    def get_title_without_year(self):
        # 去除形如 (20xx) 的部分，包含左右括号
        return re.sub(r'\s*\(20\d{2}\)', '', self.title)

    def get_default_cloud_path(self):
        return f'/{settings.cloud_base_path}/{self.tv_category}/{self.get_year()}/{self.get_title_without_year()}'

