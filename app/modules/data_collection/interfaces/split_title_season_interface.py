import copy
from abc import ABC, abstractmethod
from typing import List, Tuple

from tensorflow.python.ops.gen_array_ops import deep_copy

from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.utils.lazy_load import lazy


class ISplitTitleSeasonInterface(ABC):

    @abstractmethod
    async def get_title(self,target_title_season:str,title_seasons:Tuple[str])->str:
        """
        获取目标target_title_season对应的title，title_seasons主要用于ai能够一次性处理所有title_season节省ai对话资源
        :param target_title_season:
        :param title_seasons:
        :return:
        """
    @abstractmethod
    async def get_season(self,target_title_season:str,title_seasons:Tuple[str])->str:
        """
        获取目标target_title_season对应的title，title_seasons主要用于ai能够一次性处理所有title_season节省ai对话资源
        :param target_title_season:
        :param title_seasons:
        :return:
        """

    async def split_title_season(self, movie_data_results: List[MovieDataSourceResult]) -> List[MovieDataSourceResult]:
        """

        :param movie_data_results:
        :return:
        """
        title_seasons=[await movie_data.title_season for movie_data in movie_data_results]
        for movie_data_result in movie_data_results:
            title = await movie_data_result.title
            season = await movie_data_result.season
            title_season=await movie_data_result.title_season
            if not title or not season:
                clone_title_seasons= copy.deepcopy(title_seasons)
                clone_title_seasons_tuple=tuple(clone_title_seasons)
                clone_title_season=copy.deepcopy(title_season)
                movie_data_result.title=lazy(lambda a=clone_title_season,b=clone_title_seasons_tuple: self.get_title(a,b))
                movie_data_result.season=lazy(lambda a=clone_title_season,b=clone_title_seasons_tuple: self.get_season(a,b))
        return movie_data_results