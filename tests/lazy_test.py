import asyncio
import copy
import logging
from xml.dom.minidom import Document

from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import MovieCategory
from app.database.movie_repository import movie_repository
from app.flow.sync_new_movie_flow import combin_to_movies
from app.modules.data_collection.flow import get_douban_hot_movie_data_sources
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.data_collection.services.ai_copilot_episodes_info_provider_service import \
    ai_copilot_episodes_air_time_provider
from app.modules.data_collection.services.douban_movie_data_provider_service import \
    get_douban_movie_base_provider_service
from app.modules.data_collection.services.fallback_split_title_season_service import fallback_split_title_season_service
from app.modules.data_collection.services.fallback_tmdb_id_provider_service import fallback_tmdb_id_provider_service
from app.modules.data_collection.services.tmdb_air_date_provider_service import tmdb_air_date_provider
from app.modules.data_collection.services.tmdb_info_provider_service import tmdb_infos_provider_service
from app.services.movie_service import movie_service
from app.utils.lazy_load import lazy

logger=logging.getLogger(__name__)


async def f():
    all_movie_data_sources = []
    for i in range(10):
        movie_data_source = MovieDataSourceResult()

        copy.deepcopy(movie_data_source)
        all_movie_data_sources.append(movie_data_source)

    for i in all_movie_data_sources:
        await i.title_season

async def main():
    await init_db()
    setup_logging()
    tasks=[f() for i in range(2)]
    await asyncio.gather(*tasks)




if __name__ == '__main__':
    asyncio.run(main())