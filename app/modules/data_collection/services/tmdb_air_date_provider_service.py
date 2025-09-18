import asyncio
import logging
from typing import List, Tuple

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import EpisodesInfo
from app.modules.data_collection.interfaces.episodes_air_date_provider_interface import IEpisodesAirDateProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.utils.cache import async_ttl_cache
import tmdbsimple as tmdb
logger=logging.getLogger(__name__)
class TMDBAirDateProviderService(IEpisodesAirDateProvider):
    async def _fetch_infos(self, tmdb_id: int, season_number: int) -> List[EpisodesInfo]:

        """
        缓存60秒
        :return:
        """
        # 查找特定季

        tv_season = tmdb.TV_Seasons(tv_id=tmdb_id, season_number=season_number)
        response = tv_season.info(language='zh-CN')
        logger.debug(f'tv_info response={response}')
        if response['episodes']:
            episodes_infos = response['episodes']
            episodes_info_results=[
                EpisodesInfo(
                    air_date=episodes_info['air_date'],
                    episode_number=episodes_info['episode_number'],
                )
                for episodes_info in episodes_infos
            ]
            logger.debug(f'episodes_infos={episodes_info_results}')
            return episodes_info_results


        raise Exception('episodes not found')

    async def get_air_date(self, movie_data_source: MovieDataSourceResult) -> List[EpisodesInfo]:
        tmdb_infos =await movie_data_source.tmdb_infos
        tmdb_id=tmdb_infos.id
        season=tmdb_infos.season_number
        title_season=await movie_data_source.title_season
        if not tmdb_id or  season is None:
            logger.warning(f'title_season={title_season}, tmdb_id={tmdb_id}, season={season} tmdb_id和tmdb_season至少一个为空，无法搜索tmdb数据库')
        tmdb_episodes_infos = await self._fetch_infos(tmdb_id=tmdb_id, season_number=season)
        episodes_infos=await movie_data_source.episodes_info
        episodes_infos_map={
            e.episode_number:e for e in episodes_infos
        }
        for tmdb_episodes_info in tmdb_episodes_infos:
            if val:= episodes_infos_map.get(tmdb_episodes_info.episode_number):
                val.air_date=tmdb_episodes_info.air_date


        return episodes_infos
tmdb_air_date_provider = TMDBAirDateProviderService()
async def main():
    await init_db()
    setup_logging()
    tmdb.API_KEY=settings.TMDB_API_KEY
    await tmdb_air_date_provider._fetch_infos(tmdb_id=253093, season_number=1)
if __name__ == '__main__':
    asyncio.run(main())
