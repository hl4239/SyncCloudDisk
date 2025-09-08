import asyncio
import json
from logging import getLogger
from typing import List, Tuple, Optional



from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.models import Movie, MovieType
from app.modules.data_collection.interfaces.current_episodes_provider_interface import ICurrentEpisodesProvider
from app.modules.data_collection.interfaces.total_episodes_provider_interface import ITotalEpisodesProvider
import tmdbsimple as tmdb

from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.movie_service import movie_service
from app.utils.cache import async_ttl_cache

logger=getLogger(__name__)
class TMDBEpisodesProviderService(ICurrentEpisodesProvider,ITotalEpisodesProvider):


    @async_ttl_cache(ttl=60)
    async def _fetch_infos(self,tmdb_id:int,season_number:int)->Tuple[str,str]:

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
            current_episodes_number=episodes_info[-1]['episode_number']
            episode_type=episodes_info[-1]['episode_type']
            if episode_type=='finale':
                total_episodes_number=current_episodes_number
                return movie_service.number_to_current_episodes(current_episodes_number,is_finale=True),movie_service.number_to_total_episodes(total_episodes_number)
            else:
                return movie_service.number_to_current_episodes(current_episodes_number,is_finale=False),''

        raise Exception('episodes not found')

    async def get_current_episodes(self, movie_result: MovieDataSourceResult) -> Optional[str]:
        tmdb_infos=await movie_result.tmdb_infos
        if tmdb_infos.id and (tmdb_infos.season_number is not None):
            current_episodes,_=await self._fetch_infos(tmdb_infos.id, tmdb_infos.season_number)
            logger.debug(f'get_current_episodes={current_episodes} title={await movie_result.title} tmdb_infos={tmdb_infos}')
            return current_episodes
        logger.debug(f'get_current_episodes={None} title={await movie_result.title} tmdb_infos={tmdb_infos}')
        return None
    async def get_total_episodes(self, movie_data: MovieDataSourceResult) ->  Optional[str]:
        tmdb_infos = await movie_data.tmdb_infos
        if tmdb_infos.id and (tmdb_infos.season_number is not None):
            _, total_episodes = await self._fetch_infos(tmdb_infos.id,tmdb_infos.season_number)
            logger.debug(f'get_total_episodes={total_episodes} title={await movie_data.title} tmdb_infos={tmdb_infos}')
            return total_episodes
        logger.debug(f'get_total_episodes={None} title={await movie_data.title} tmdb_infos={tmdb_infos}')
        return None




tmdb_episodes_provider_service=TMDBEpisodesProviderService()
current_episodes_provider_service=tmdb_episodes_provider_service
total_episodes_provider_service=tmdb_episodes_provider_service
async def main():
    a,b= await tmdb_episodes_provider_service._fetch_infos(280945,0)
    print(a,b)
if __name__ == '__main__':
    tmdb.API_KEY=settings.TMDB_API_KEY
    setup_logging()
    asyncio.run(main())
