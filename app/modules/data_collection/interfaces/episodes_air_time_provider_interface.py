import copy
import logging
from abc import abstractmethod, ABC
from typing import List

from app.database.models import EpisodesInfo, MovieType
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.movie_service import movie_service
from app.utils.lazy_load import lazy

logger=logging.getLogger(__name__)
class IEpisodesAirTimeProvider(ABC):
    @abstractmethod
    async def get_air_time(self,movie_data_source:MovieDataSourceResult) ->  List[EpisodesInfo]:
        ...

    async def set_air_time(self,movie_data_sources:List[MovieDataSourceResult])->List[MovieDataSourceResult]:
        """
        在已有的 list episodes_info 中对air_time补充
        :param movie_data_sources:
        :return:
        """
        for movie_data_result in movie_data_sources:
            if await movie_data_result.movie_type == MovieType.TV:
                episodes_info = await movie_data_result.episodes_info
                if not movie_service.is_air_time_full(episodes_info)and not movie_service.is_finale(episodes_info):
                    logger.debug(
                        f'开始注册air_time设置回调：title={await movie_data_result.title}')
                    copy_movie_data = copy.deepcopy(movie_data_result)
                    movie_data_result.episodes_info = lazy(lambda c=copy_movie_data: self.get_air_time(c))
                else:
                    logger.debug(
                        f'无需注册ait_time设置回调：title={await movie_data_result.title} episodes_info={episodes_info}')
        return movie_data_sources