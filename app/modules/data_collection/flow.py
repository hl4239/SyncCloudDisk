import asyncio
from logging import getLogger
from typing import List

import tmdbsimple
from dependency_injector.wiring import Provide, inject
from prefect import task, flow
from prefect.cache_policies import NO_CACHE

import app
from app.core.config import settings
from app.core.container import ProjectContainer
from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import TVCategory
from app.modules.data_collection.container import DataCollectionContainer
from app.modules.data_collection.interfaces.match_to_database_interface import IMatchToDatabase
from app.modules.data_collection.interfaces.movie_base_provider_interface import IMovieBaseProvider
from app.modules.data_collection.interfaces.split_title_season_interface import ISplitTitleSeasonInterface
from app.modules.data_collection.interfaces.tmdb_id_provider_interface import ITMDBIDProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult

logger=getLogger(__name__)
@inject
@task(cache_policy=NO_CACHE)# @task(cache_policy=NO_CACHE)  # 或者 @task(cache_key_fn=task_input_hash)
async def get_hot(categories:List[TVCategory],count: int = 10,movie_base_provider_factory:IMovieBaseProvider=Provide[DataCollectionContainer.movie_base_provider_service])->List[MovieDataSourceResult]:
        movie_base_service=await movie_base_provider_factory
        result=await movie_base_service.get_hot_movies(categories,count)
        return result
@inject
@task
async def match_to_database(movie_data_results:List[MovieDataSourceResult],match_to_database_service:IMatchToDatabase=Provide[DataCollectionContainer.match_to_database_service]) -> List[MovieDataSourceResult]:
    result= await match_to_database_service.match(movie_data_results)
    return result

@inject
@task
async def split_title_season(movie_data_results:List[MovieDataSourceResult],split_title_season_service:ISplitTitleSeasonInterface=Provide[DataCollectionContainer.split_title_season_service]) -> List[MovieDataSourceResult]:
    result=await split_title_season_service.split_title_season(movie_data_results)
    return result

@inject
@task
async def get_tmdb_id(movie_data_results:List[MovieDataSourceResult],tmdb_id_provider_service:ITMDBIDProvider=Provide[DataCollectionContainer.tmdb_id_provider_service])->List[MovieDataSourceResult]:
    result=await tmdb_id_provider_service.set_id(movie_data_sources=movie_data_results)
    return result

@flow
async def data_collection_get_hot_flow(i:str):
        hot_resp= await get_hot(categories=[TVCategory.CHINA,TVCategory.KOREA],count=5)

        match_resp= await match_to_database(movie_data_results=hot_resp)

        split_resp= await split_title_season(movie_data_results=match_resp)
        for item in split_resp:
            logger.debug(f'title={await item.title} season={await item.season}')
        # get_tmdb_id_resp=await get_tmdb_id(split_resp)

        return hot_resp


async def main():
    setup_logging()
    await init_db()
    tmdbsimple.API_KEY = settings.TMDB_API_KEY
    project_container = ProjectContainer()
    logger.info(__name__)

    project_container.data_collection_container().wire(app.modules.data_collection.flow)
    await project_container.data_collection_container().init_resources()
    # wire_all(project_container)
    # await project_container.data_collection_container().shutdown_resources()
    data_collection_context = project_container.data_collection_context()
    await data_collection_get_hot_flow('asdas')
    await project_container.data_collection_container().shutdown_resources()
    # await init_app()
    # data_collection_context=project_container.data_collection_context()
    # await data_collection_get_hot_flow('asdas')
    # await project_container.data_collection_container().shutdown_resources()
if __name__ == '__main__':
    asyncio.run(main())
