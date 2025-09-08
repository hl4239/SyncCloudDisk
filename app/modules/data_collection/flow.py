import asyncio
from logging import getLogger
from typing import List

import tmdbsimple


from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import TVCategory
from app.modules.data_collection.interfaces.current_episodes_provider_interface import ICurrentEpisodesProvider
from app.modules.data_collection.interfaces.match_to_database_interface import IMatchToDatabase
from app.modules.data_collection.interfaces.movie_base_provider_interface import IMovieBaseProvider
from app.modules.data_collection.interfaces.split_title_season_interface import ISplitTitleSeasonInterface
from app.modules.data_collection.interfaces.tmdb_id_provider_interface import ITMDBIDProvider
from app.modules.data_collection.interfaces.total_episodes_provider_interface import ITotalEpisodesProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.data_collection.services.douban_movie_data_provider_service import \
    get_douban_movie_base_provider_service
from app.modules.data_collection.services.fallback_split_title_season_service import \
     fallback_split_title_season_service
from app.modules.data_collection.services.fallback_tmdb_id_provider_service import fallback_tmdb_id_provider_service

from app.modules.data_collection.services.match_to_database_service import match_to_database_service
from app.modules.data_collection.services.tmdb_episodes_provider_service import total_episodes_provider_service, \
    current_episodes_provider_service

logger=getLogger(__name__)
# @task(cache_policy=NO_CACHE)# @task(cache_policy=NO_CACHE)  # 或者 @task(cache_key_fn=task_input_hash)
async def get_hot(categories:List[TVCategory],count: int ,movie_base_provider_service:IMovieBaseProvider)->List[MovieDataSourceResult]:
        result=await movie_base_provider_service.get_hot_movies(categories,count)
        return result
# @task
async def match_to_database(movie_data_results:List[MovieDataSourceResult],match_to_database_service:IMatchToDatabase) -> List[MovieDataSourceResult]:
    result= await match_to_database_service.match(movie_data_results)
    return result

# @task
async def split_title_season(movie_data_results:List[MovieDataSourceResult],split_title_season_service:ISplitTitleSeasonInterface) -> List[MovieDataSourceResult]:
    result=await split_title_season_service.split_title_season(movie_data_results)
    return result

# @task
async def set_tmdb_id(movie_data_results:List[MovieDataSourceResult],tmdb_id_provider_service:ITMDBIDProvider)->List[MovieDataSourceResult]:
    result=await tmdb_id_provider_service.set_id(movie_data_sources=movie_data_results)
    return result

async def set_current_episodes(movie_data_results:List[MovieDataSourceResult],current_episodes_provider_service_:ICurrentEpisodesProvider)->List[MovieDataSourceResult]:
    result=await current_episodes_provider_service_.set_current_episodes(movie_data_results)
    return result

async def set_total_episodes(movie_data_results:List[MovieDataSourceResult],total_episodes_provider_service_:ITotalEpisodesProvider)->List[MovieDataSourceResult]:
    result=await total_episodes_provider_service_.set_total_episodes(movie_data_results)
    return result

# @flow
async def data_collection_get_hot_flow(categories:List[TVCategory],count:int):
        hot_resp= await get_hot(categories=categories,count=count,movie_base_provider_service=await get_douban_movie_base_provider_service())

        match_resp= await match_to_database(movie_data_results=hot_resp,match_to_database_service=match_to_database_service)

        split_resp= await split_title_season(movie_data_results=match_resp,split_title_season_service=fallback_split_title_season_service)

        get_tmdb_id_resp=await set_tmdb_id(split_resp,tmdb_id_provider_service=fallback_tmdb_id_provider_service)

        set_total_episodes_resp=await set_total_episodes(get_tmdb_id_resp,total_episodes_provider_service_=total_episodes_provider_service)

        set_current_episodes_resp=await set_current_episodes(set_total_episodes_resp,current_episodes_provider_service_=current_episodes_provider_service)


        for item in set_current_episodes_resp:
            logger.debug(f'title={await item.title} season={await item.season} tmdb_infos={await item.tmdb_infos} current_episodes={await item.current_episodes} total_episodes={await item.total_episodes}')
        return hot_resp



async def main():
    setup_logging()
    await init_db()
    tmdbsimple.API_KEY = settings.TMDB_API_KEY

    await data_collection_get_hot_flow(categories=[TVCategory.CHINA],count=1)

if __name__ == '__main__':
    asyncio.run(main())
