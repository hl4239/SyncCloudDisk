from abc import ABC, abstractmethod
from typing import List, Tuple

from app.core.logging_config import get_logger
from app.database.models import TMDBInfos
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.utils.lazy_load import lazy

logger=get_logger(__name__)


class ITMDBIDProvider(ABC):
    @abstractmethod
    async def get_tmdb_id(self, movie_data_source: MovieDataSourceResult) -> Tuple[int,int]:
        ...

    async def get_tmdb_infos(self,movie_data_source:MovieDataSourceResult)->TMDBInfos|None:

        tmdb_infos = TMDBInfos()
        id_,season= await self.get_tmdb_id(movie_data_source)
        # 电影可以不存在season
        if id_ or season :
            return TMDBInfos(id=id_,season_number=season)
        return TMDBInfos()

    async def set_id(self, movie_data_sources: List[MovieDataSourceResult]) -> List[MovieDataSourceResult]:
        for movie_data_source in movie_data_sources:

            movie_data_source.tmdb_infos = lazy(lambda c=movie_data_source: self.get_tmdb_infos(c))

        return movie_data_sources

