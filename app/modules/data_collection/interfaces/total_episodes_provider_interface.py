import copy
from abc import ABC, abstractmethod
from logging import getLogger
from typing import List

from app.database.models import Movie, MovieType
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.movie_service import movie_service
from app.utils.lazy_load import lazy

logger=getLogger(__name__)
class ITotalEpisodesProvider(ABC):

    @abstractmethod
    async def get_total_episodes(self,movie_data:MovieDataSourceResult) -> str:
        ...

    async def set_total_episodes(self, movie_data_results: List[MovieDataSourceResult]) -> List[MovieDataSourceResult]:
        """
        获取影视的总剧集
        :param movie_data_results:
        :return:
        """
        for movie_data_result in movie_data_results:
            if await movie_data_result.movie_type ==MovieType.TV:
                total_episodes = await movie_data_result.total_episodes
                if not total_episodes:
                    logger.debug(f'开始注册总剧集回调：title={await movie_data_result.title} total_episodes={total_episodes}')
                    copy_movie_data=copy.deepcopy(movie_data_result)
                    movie_data_result.total_episodes=lazy(lambda c=copy_movie_data: self.get_total_episodes(c))
                else:
                    logger.debug(
                        f'无需注册总剧集回调：title={await movie_data_result.title} total_episodes={total_episodes}')
        return movie_data_results


