import copy
import logging
from abc import ABC, abstractmethod
from typing import List

from app.database.models import MovieType, EpisodesInfo
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.movie_service import movie_service
from app.utils.lazy_load import lazy

logger=logging.getLogger(__name__)
class IEpisodesInfosProvider(ABC):
    @abstractmethod
    async def get_episodes_infos(self,movie_data_source:MovieDataSourceResult) -> List[EpisodesInfo]:
        ...

    async def set_episodes_infos(self,movie_data_sources:List[MovieDataSourceResult])->List[MovieDataSourceResult]:
        """
        如果episodes_infos为none则创建，如果len<total_episodes则扩充
        :param movie_data_sources:
        :return:
        """
        for movie_data_result in movie_data_sources:
            if await movie_data_result.movie_type == MovieType.TV:
                episodes_infos = await movie_data_result.episodes_info
                total_episodes = await movie_data_result.total_episodes
                if  episodes_infos is None or len(episodes_infos) <movie_service.extract_episode_number(total_episodes) :
                    logger.debug(
                        f'开始注册episodes_infos设置回调：title={await movie_data_result.title}')
                    copy_movie_data = copy.deepcopy(movie_data_result)
                    movie_data_result.episodes_info = lazy(lambda c=copy_movie_data: self.get_episodes_infos(c))
                else:
                    logger.debug(
                        f'无需注册episodes_infos设置回调：title={await movie_data_result.title} episodes_info={episodes_infos}')
        return movie_data_sources