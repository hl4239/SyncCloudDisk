# prefect_flow_async.py
import asyncio
import logging
from typing import List

import tmdbsimple
from dependency_injector.wiring import inject, Provide, Container
from prefect import flow, task, get_run_logger

from app.adapters.movie_data_source_adapter import MovieDataSourceAdapter
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import Movie, TVCategory
from app.database.movie_repository import movie_repository
from app.modules.data_collection.context import DataCollectionContext
from app.modules.data_collection.flow import data_collection_get_hot_flow
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.episodes_filter.context import EpisodesFilterContext
from app.modules.episodes_filter.schemas import EpisodesFilterResult
from app.modules.link_parse.context import LinkParseContext
from app.modules.link_parse.schemas import LinkParseResult

from app.modules.link_scraping.context import LinkScrapeContext
from app.modules.link_scraping.schemes.link import LinkScrapeResult
from app.services.movie_service import movie_service
logger=logging.getLogger(__name__)

@task
async def collect_data_hot(categories:List[TVCategory],count=1)->List[MovieDataSourceResult]:
    return await data_collection_get_hot_flow(categories,count)

@task
async def adapt_to_movies(movie_data_source:List[MovieDataSourceResult])->List[Movie]:
    ...
@task
async def link_scraping(movies:List[Movie])->List[LinkScrapeResult]:
    ...
@task
async def link_parse(link_scrape_datas)->List[LinkParseResult]:
    ...

@task
async def episodes_filter_for_update(link_parse_results:List[LinkScrapeResult])->List[EpisodesFilterResult]:
    ...
@task
async def combin_to_movies(movie_datas_sources:List[MovieDataSourceResult])->List[Movie]:
    return await movie_service.combin_to_movies(movie_datas_sources)

@task
async def save_to_database(movies:List[Movie]):
    await movie_repository.upsert(movies,ignore_none=True)


@flow
async def flow1():
    movie_data_source_results=  await collect_data_hot([TVCategory.CHINA,TVCategory.KOREA],count=5)
    combin_results=await combin_to_movies(movie_data_source_results)
    logger.debug(combin_results)

    await save_to_database(combin_results)
async def main():
    await init_db()
    setup_logging()
    tmdbsimple.API_KEY = settings.TMDB_API_KEY
    await flow1()

if __name__ == '__main__':
    asyncio.run(main())
