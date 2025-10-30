from typing import Tuple

from app.modules.data_collection.interfaces.tmdb_id_provider_interface import ITMDBIDProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult


class AnimationTMDBIDProvider(ITMDBIDProvider):
    """
    tv版动漫，不包含电影
    """
    async def get_tmdb_id(self, movie_data_source: MovieDataSourceResult) -> Tuple[int, int]:
        pass

