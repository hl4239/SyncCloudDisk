from datetime import datetime
from logging import getLogger

from app.modules.data_collection.interfaces.current_episodes_provider_interface import ICurrentEpisodesProvider
from app.modules.data_collection.interfaces.total_episodes_provider_interface import ITotalEpisodesProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.movie_service import movie_service
from app.utils.cache import async_ttl_cache
import tmdbsimple as tmdb
logger=getLogger(__name__)
class V2TmdbEpisodesProviderService(ITotalEpisodesProvider,ICurrentEpisodesProvider):
    @async_ttl_cache(ttl=60)
    async def _fetch_infos(self, tmdb_id: int, season_number: int) -> EpisodesInfo:

        """
        缓存60秒
        :param id:
        :return:
        """
        # 查找特定季
        tv_season = tmdb.TV_Seasons(tv_id=tmdb_id, season_number=season_number)
        response = tv_season.info(language='zh-CN')
        logger.debug(f'tv_info response={response}')
        if response['episodes']:
            episodes_info = response['episodes']
            episodes_info_=EpisodesInfo(episode_number=episodes_info['episode_number'], air_date= datetime.strptime(episodes_info['air_date'], "%Y-%m-%d"))
            logger.info(f'episodes_info response={episodes_info_}')
            return episodes_info_
        raise Exception('episodes not found')



    async def get_total_episodes(self, movie_data: MovieDataSourceResult) -> str:
        pass

    async def get_current_episodes(self, movie_result: MovieDataSourceResult) -> str:
        pass