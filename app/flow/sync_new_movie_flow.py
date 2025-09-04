# prefect_flow_async.py
import asyncio
from typing import List

from dependency_injector.wiring import inject, Provide, Container
from prefect import flow, task, get_run_logger

from app.adapters.movie_data_source_adapter import MovieDataSourceAdapter
from app.core.container import ProjectContainer
from app.database.database import init_db
from app.database.models import Movie
from app.modules.data_collection.context import DataCollectionContext
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.episodes_filter.context import EpisodesFilterContext
from app.modules.episodes_filter.schemas import EpisodesFilterResult
from app.modules.link_parse.context import LinkParseContext
from app.modules.link_parse.schemas import LinkParseResult

from app.modules.link_scraping.context import LinkScrapeContext
from app.modules.link_scraping.schemes.link import LinkScrapeResult


@inject
@task
async def collect_data_hot(collect_data_context:DataCollectionContext = Provide[ProjectContainer.data_collection_context],)->List[MovieDataSourceResult]:
    return await collect_data_context.run_hot()

@task
async def adapt_to_movies(movie_data_source:List[MovieDataSourceResult],adapter:MovieDataSourceAdapter=Provide[ProjectContainer.data_collection_context])->List[Movie]:
    return await adapter.to_movies(movie_data_source)

@task
async def link_scraping(movies:List[Movie],link_scraper:LinkScrapeContext=Provide[ProjectContainer.link_scrape_context])->List[LinkScrapeResult]:
    return await link_scraper.scrape(movies)
@task
async def link_parse(link_scrape_datas:List[LinkScrapeResult],link_parser:LinkParseContext=Provide[ProjectContainer.link_parse_context])->List[LinkParseResult]:
    return await link_parser.parse(link_scrape_datas)

@task
async def episodes_filter_for_update(link_parse_results:List[LinkScrapeResult],episodes_filter:EpisodesFilterContext=Provide[ProjectContainer.episodes_filter_context])->List[EpisodesFilterResult]:
    return await episodes_filter.get_new_episodes(link_parse_results)



@flow
async def flow1():
    await collect_data_hot()

async def main():
    await init_db()
    project_container = ProjectContainer()
    project_container.wire(modules=[__name__])
    data_collection_context=project_container.data_collection_context()
    await flow1()

if __name__ == '__main__':
    asyncio.run(main())
