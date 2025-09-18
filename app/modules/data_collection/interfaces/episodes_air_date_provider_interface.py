import copy
from abc import ABC, abstractmethod
from logging import getLogger
from typing import List

from app.database.models import MovieType, EpisodesInfo
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.movie_service import movie_service
from app.utils.lazy_load import lazy

logger=getLogger(__name__)
class IEpisodesAirDateProvider(ABC):
    @abstractmethod
    async def get_air_date(self,movie_data_source:MovieDataSourceResult) ->  List[EpisodesInfo]:
        ...

    async def set_air_date(self,movie_data_sources:List[MovieDataSourceResult])->List[MovieDataSourceResult]:
        """
        对已存在的episodes_infos补充air_date,不会创建新的或改变长度

        :param movie_data_sources:
        :return:
        """
        for movie_data_result in movie_data_sources:
            if await movie_data_result.movie_type == MovieType.TV:
                episodes_info = await movie_data_result.episodes_info
                total_episodes=await movie_data_result.total_episodes
                if not movie_service.is_air_date_full(episodes_info,):
                    logger.debug(
                        f'开始注册剧集日历设置回调：title={await movie_data_result.title}')
                    copy_movie_data = copy.deepcopy(movie_data_result)
                    movie_data_result.episodes_info = lazy(lambda c=copy_movie_data: self.get_air_date(c))
                else:
                    logger.debug(
                        f'无需注册剧集日历设置回调：title={await movie_data_result.title} episodes_info={episodes_info}')
        return movie_data_sources