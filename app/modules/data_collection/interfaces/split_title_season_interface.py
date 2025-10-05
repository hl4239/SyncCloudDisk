import copy
from abc import ABC, abstractmethod
from typing import List, Tuple


from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.utils.lazy_load import lazy, Lazy


class ISplitTitleSeasonInterface(ABC):

    @abstractmethod
    async def get_title(self,target_title_season:Lazy[str],title_seasons:List[Lazy[str]])->str:
        """
        获取目标target_title_season对应的title，title_seasons主要用于ai能够一次性处理所有title_season节省ai对话资源
        :param target_title_season:
        :param title_seasons:
        :return:
        """
    @abstractmethod
    async def get_season(self,target_title_season:Lazy[str],title_seasons:List[Lazy[str]])->str:
        """
        获取目标target_title_season对应的title，title_seasons主要用于ai能够一次性处理所有title_season节省ai对话资源
        :param target_title_season:
        :param title_seasons:
        :return:
        """

