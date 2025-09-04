from typing import List

from app.database.models import Movie
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult


class MovieDataSourceAdapter:
    async def to_movies(self, movie_data_sources:List[MovieDataSourceResult]) -> List[Movie]:
        ...
    async def to_movie(self,movie_data_source)->Movie:
        ...