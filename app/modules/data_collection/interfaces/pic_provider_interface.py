import logging
from abc import ABC
from typing import List

from app.modules.data_collection.interfaces.total_episodes_provider_interface import ITotalEpisodesProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult

logger=logging.getLogger(__name__)
class IPicProvider(ABC):

    async def set_pic(self, movie_data_results: List[MovieDataSourceResult]) -> List[MovieDataSourceResult]:
        """
        如果总剧集不存在则获取
        :param movie_data_results:
        :return:
        """
        for movie_data_result in movie_data_results:
            if await movie_data_result.pic ==MovieType.TV:
                total_episodes = await movie_data_result.total_episodes
                if not total_episodes:
                    logger.debug(f'开始注册海报回调：title={await movie_data_result.title} total_episodes={total_episodes}')
                    movie_data_result.total_episodes=lazy(lambda c=movie_data_result: self.get_total_episodes(c))
                else:
                    logger.debug(
                        f'无需注册海报回调：title={await movie_data_result.title} total_episodes={total_episodes}')
        return movie_data_results
