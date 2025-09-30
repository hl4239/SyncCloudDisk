import asyncio
import logging
from typing import Tuple

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.models import MovieType
from app.modules.data_collection.interfaces.tmdb_id_provider_interface import ITMDBIDProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.data_collection.services.a_tmdb_id_provider_service import a_tmdb_id_provider_service
from app.modules.data_collection.services.b_tmdb_provider_service import b_tmdb_provider_service
from app.utils.lazy_load import lazy
import tmdbsimple as tmdb
logger=logging.getLogger(__name__)
class FallbackTMDBIDProviderService(ITMDBIDProvider):
    def __init__(self,a_tmdb_id_provider_service,b_tmdb_id_provider_service):
        self.a_tmdb_id_provider_service = a_tmdb_id_provider_service
        self.b_tmdb_id_provider_service = b_tmdb_id_provider_service

    async def get_tmdb_id(self, movie_data_source: MovieDataSourceResult) -> Tuple[int, int]:
        logger.debug(f"正在执行a_tmdb_id_provider")
        r= await self.a_tmdb_id_provider_service.get_tmdb_id(movie_data_source)
        if not r:
            logger.warning(f"未从a_tmdb_id_provider获取到tmdb信息，正在执行b")
            r=await self.b_tmdb_id_provider_service.get_tmdb_id(movie_data_source)
        if r:
            logger.info(f'从tmdb_info_provider获取到{r}')
            tmdb_id=r[0]
            season_number=r[1]
        else:
            logger.warning(f"未从b_tmdb_id_provider获取到tmdb信息，将返回tmdb_info.id tmdb_info.season_number 为None")
            tmdb_id=None
            season_number=None
        return tmdb_id,season_number
fallback_tmdb_id_provider_service = FallbackTMDBIDProviderService(a_tmdb_id_provider_service=a_tmdb_id_provider_service,b_tmdb_id_provider_service=b_tmdb_provider_service)
async def main():
    tmdb.API_KEY = settings.TMDB_API_KEY
    setup_logging()
    movie_data_sources=[MovieDataSourceResult(title_season=lazy('凡人修仙传：重返天南'),
                                              title=lazy('凡人修仙传'),
                                              season=lazy('重返天南'),
                                              movie_type=lazy(MovieType.TV),
                                              year= lazy('2025'))
                        ]
    result= await fallback_tmdb_id_provider_service.set_id(movie_data_sources)

if __name__ == '__main__':
    asyncio.run(main())