import copy
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

    async def get_tmdb_infos(self,movie_data_source:MovieDataSourceResult)->TMDBInfos:
        print(f'title_season={await movie_data_source.title_season}' )
        tmdb_infos = await movie_data_source.tmdb_infos
        print(f'tmdb_infos={tmdb_infos}')
        if tmdb_infos:
            if tmdb_infos.id:
                return tmdb_infos
        else:
            tmdb_infos = TMDBInfos()
        try:
            tmdb_infos.id,tmdb_infos.season_number = await self.get_tmdb_id(movie_data_source)
            tmdb_infos.not_ensure=False
        except TMDBIDNotFound as e:
            logger.info(e)

        except TMDBIDNotEnsure as e:
            logger.info(e)
            tmdb_infos.not_ensure=True
        return tmdb_infos

    async def set_id(self, movie_data_sources: List[MovieDataSourceResult]) -> List[MovieDataSourceResult]:
        for movie_data_source in movie_data_sources:
            cloned_model = copy.deepcopy(movie_data_source)
            logger.debug(f'cloned_model={cloned_model.title_season}')
            movie_data_source.tmdb_infos = lazy(lambda c=cloned_model: self.get_tmdb_infos(c))

        return movie_data_sources

class TMDBIDNotEnsure(Exception):
    ...
class TMDBIDNotFound(Exception):
    ...