import copy
from abc import ABC, abstractmethod
from logging import getLogger
from typing import List

from tensorflow.python.ops.gen_array_ops import deep_copy

from app.database.models import Movie, MovieType
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.movie_service import movie_service
from app.utils.lazy_load import lazy

logger=getLogger(__name__)
class ICurrentEpisodesProvider(ABC):


    @abstractmethod
    async def get_current_episodes(self,movie_result:MovieDataSourceResult) -> str:
        ...

    async def set_current_episodes(self,movie_data_results:List[MovieDataSourceResult])->List[MovieDataSourceResult]:
        """
        获取影视当前更新的剧集
        :param movie_data_results:
        :return:
        """
        for movie_data_result in movie_data_results:
            if await movie_data_result.movie_type ==MovieType.TV:

                current_episodes = await movie_data_result.current_episodes
                if not (current_episodes and movie_service.is_finale(current_episodes)):
                # if not current_episodes:
                    logger.debug(f'开始注册最新剧集回调：title={await movie_data_result.title} current_episodes={await movie_data_result.current_episodes}')
                    copy_movie_data=copy.deepcopy(movie_data_result)
                    movie_data_result.current_episodes=lazy(lambda c=copy_movie_data: self.get_current_episodes(c))
                else:
                    logger.debug(f'无需注册最新剧集回调：title={await movie_data_result.title} current_episodes={await movie_data_result.current_episodes}')
        return movie_data_results