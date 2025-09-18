
# prefect_flow_async.py
import asyncio
import logging
from typing import List
import tmdbsimple
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import Movie, TVCategory
from app.database.movie_repository import movie_repository
from app.modules.data_collection.flow import data_collection_get_hot_flow
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.filter.flow import filter_flow
from app.modules.filter.schemas import TargetEpisodeFilterResult
from app.modules.link_parse.flow import link_parse_flow_parses
from app.modules.link_parse.schemas import LinkParseResult, PrepareParseLinks

from app.modules.link_scraping.flow import link_scrape_flow_search
from app.modules.link_scraping.schemes.link import LinkScrapeResult
from app.services.movie_service import movie_service
logger=logging.getLogger(__name__)

# @task
async def collect_data_hot(categories:List[TVCategory],count=1)->List[MovieDataSourceResult]:
    return await data_collection_get_hot_flow(categories,count)

# @task
async def adapt_to_movies(movie_data_source:List[MovieDataSourceResult])->List[Movie]:
    ...
# @task
async def link_scraping(movies:List[Movie],count:int)->List[LinkScrapeResult]:
    results= await link_scrape_flow_search(movies,count)
    return results
# @task
async def link_parse(link_scrape_datas:List[PrepareParseLinks])->List[LinkParseResult]:
    results= await link_parse_flow_parses(link_scrape_datas)
    return results

# @task
async def link_parse_result_filter(link_parse_results:List[LinkParseResult])->List[TargetEpisodeFilterResult]:
    return await filter_flow(link_parse_results)

# @task
async def combin_to_movies(movie_datas_sources:List[MovieDataSourceResult])->List[Movie]:
    return await movie_service.combin_to_movies(movie_datas_sources)

# @task
async def save_to_database(movies:List[Movie]):
    await movie_repository.upsert(movies,ignore_none=True)



# @flow
async def flow1():
    movie_data_source_results=  await collect_data_hot([TVCategory.CHINA,TVCategory.KOREA],count=10)
    movies=await combin_to_movies(movie_data_source_results)
    await save_to_database(movies)
    scrape_results= await link_scraping(movies,count=3)
    parses_results = await link_parse([PrepareParseLinks(scrape_quark_links=s.quark_links,movie=s.movie)for s in scrape_results])
    filter_results=await link_parse_result_filter(parses_results)
    for i in filter_results:
        print( i.movie )



async def main():
    await init_db()
    setup_logging()
    tmdbsimple.API_KEY = settings.TMDB_API_KEY
    await flow1()

if __name__ == '__main__':
    asyncio.run(main())
