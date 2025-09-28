from typing import List

from app.database.models import Movie
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult


class MovieDataSourceAdapter:

    @classmethod
    async def to_movies(cls, movie_data_sources:List[MovieDataSourceResult]) -> List[Movie]:
        movies= []
        for movie_data_source in movie_data_sources:
            movie=await cls.to_movie(movie_data_source)
            movies.append(movie)
        return movies
    @staticmethod
    async def to_movie(movie_data_source:MovieDataSourceResult)->Movie:
        title = await movie_data_source.title
        douban_id = await movie_data_source.douban_id
        title_season = await movie_data_source.title_season
        subtitle = await movie_data_source.subtitle
        description = await movie_data_source.description
        year = await movie_data_source.year
        category = await movie_data_source.category
        movie_type = await movie_data_source.movie_type
        season = await movie_data_source.season
        total_episodes = await movie_data_source.total_episodes
        status = await movie_data_source.status
        tmdb_infos = await movie_data_source.tmdb_infos
        movie_info = await movie_data_source.movie_info

        movie=Movie(title=title,douban_id=douban_id,title_season=title_season,subtitle=subtitle
                    ,description=description,year=year,category=category,movie_type=movie_type
                    ,season=season,total_episodes=total_episodes,


                    tmdb_infos=tmdb_infos,
        )
        return movie



movie_data_source_adapter=MovieDataSourceAdapter()