import asyncio
from logging import getLogger
from typing import List, Dict, Tuple

import tmdbsimple


from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import MovieType, MovieCategory
from app.modules.data_collection.interfaces.episodes_air_date_provider_interface import IEpisodesAirDateProvider
from app.modules.data_collection.interfaces.episodes_air_time_provider_interface import IEpisodesAirTimeProvider
from app.modules.data_collection.interfaces.episodes_infos_provider_interface import IEpisodesInfosProvider
from app.modules.data_collection.interfaces.match_to_database_interface import IMatchToDatabase
from app.modules.data_collection.interfaces.movie_base_provider_interface import IMovieBaseProvider
from app.modules.data_collection.interfaces.split_title_season_interface import ISplitTitleSeasonInterface
from app.modules.data_collection.interfaces.tmdb_id_provider_interface import ITMDBIDProvider
from app.modules.data_collection.interfaces.total_episodes_provider_interface import ITotalEpisodesProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.data_collection.services.ai_copilot_episodes_info_provider_service import \
    ai_copilot_episodes_air_time_provider
from app.modules.data_collection.services.douban_movie_data_provider_service import \
    get_douban_movie_base_provider_service
from app.modules.data_collection.services.episodes_info_provider_service import episodes_info_provider_service
from app.modules.data_collection.services.fallback_split_title_season_service import \
     fallback_split_title_season_service
from app.modules.data_collection.services.fallback_tmdb_id_provider_service import fallback_tmdb_id_provider_service

from app.modules.data_collection.services.match_to_database_service import match_to_database_service
from app.modules.data_collection.services.tmdb_air_date_provider_service import tmdb_air_date_provider
from app.modules.data_collection.services.tmdb_episodes_provider_service import tmdb_episodes_provider_service

logger=getLogger(__name__)
# @task(cache_policy=NO_CACHE)# @task(cache_policy=NO_CACHE)  # 或者 @task(cache_key_fn=task_input_hash)
async def get_hot(categories:List[MovieCategory],count: int ,movie_base_provider_service:IMovieBaseProvider)->List[MovieDataSourceResult]:
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



async def set_total_episodes(movie_data_results:List[MovieDataSourceResult],tmdb_episodes_provider_service:ITotalEpisodesProvider)->List[MovieDataSourceResult]:
    result=await tmdb_episodes_provider_service.set_total_episodes(movie_data_results)
    return result

async def set_air_date(movie_date_results:List[MovieDataSourceResult],episodes_air_date_provider:IEpisodesAirDateProvider)->List[MovieDataSourceResult]:
    result=await episodes_air_date_provider.set_air_date(movie_date_results)
    return result
async def set_air_time(movie_date_results:List[MovieDataSourceResult],episodes_air_time_provider:IEpisodesAirTimeProvider)->List[MovieDataSourceResult]:
    result=await episodes_air_time_provider.set_air_time(movie_date_results)
    return result
async def set_episodes_infos(movie_date_results:List[MovieDataSourceResult],episodes_info_provider:IEpisodesInfosProvider)->List[MovieDataSourceResult]:
    result=await episodes_info_provider.set_episodes_infos(movie_date_results)
    return result
# @flow
async def data_collection_get_hot_flow(categories:List[MovieCategory],count:int):
        hot_resp= await get_hot(categories=categories,count=count,movie_base_provider_service=await get_douban_movie_base_provider_service())

        match_resp= await match_to_database(movie_data_results=hot_resp,match_to_database_service=match_to_database_service)

        split_resp= await split_title_season(movie_data_results=match_resp,split_title_season_service=fallback_split_title_season_service)


        get_tmdb_id_resp=await set_tmdb_id(split_resp,tmdb_id_provider_service=fallback_tmdb_id_provider_service)

        set_total_episodes_resp=await set_total_episodes(get_tmdb_id_resp,tmdb_episodes_provider_service=tmdb_episodes_provider_service)

        set_episodes_infos_resp=await set_episodes_infos(set_total_episodes_resp,episodes_info_provider=episodes_info_provider_service)

        set_air_date_resp=await set_air_date(set_episodes_infos_resp,episodes_air_date_provider=tmdb_air_date_provider)

        set_air_time_resp=await set_air_time(set_air_date_resp,episodes_air_time_provider=ai_copilot_episodes_air_time_provider)

        return set_air_time_resp



async def get_movies_by_douban_id(params:List[Tuple[str, MovieType]]):
    r=[]
    for p in params:
        r1=await (await get_douban_movie_base_provider_service()).get_movie_by_douban_id(douban_id=p[0],movie_type=p[1])
        r.extend(r1)

    match_resp = await match_to_database(movie_data_results=r,
                                         match_to_database_service=match_to_database_service)

    split_resp = await split_title_season(movie_data_results=match_resp,
                                          split_title_season_service=fallback_split_title_season_service)

    get_tmdb_id_resp = await set_tmdb_id(split_resp, tmdb_id_provider_service=fallback_tmdb_id_provider_service)

    set_total_episodes_resp = await set_total_episodes(get_tmdb_id_resp,
                                                       tmdb_episodes_provider_service=tmdb_episodes_provider_service)

    set_episodes_infos_resp = await set_episodes_infos(set_total_episodes_resp,
                                                       episodes_info_provider=episodes_info_provider_service)

    set_air_date_resp = await set_air_date(set_episodes_infos_resp, episodes_air_date_provider=tmdb_air_date_provider)

    set_air_time_resp = await set_air_time(set_air_date_resp,
                                           episodes_air_time_provider=ai_copilot_episodes_air_time_provider)

    return set_air_time_resp
async def search_from_douban(key):
    """
    从豆瓣搜索
    :param key:
    :return:
    """
    return await (await get_douban_movie_base_provider_service()).search(keyword=key)


async def main():
    setup_logging()
    await init_db()
    tmdbsimple.API_KEY = settings.TMDB_API_KEY

    await data_collection_get_hot_flow(categories=[MovieCategory.CHINA],count=1)

if __name__ == '__main__':
    asyncio.run(main())
