from typing import List

from charset_normalizer.md import getLogger

from app.database.models import Movie
from app.database.movie_repository import MovieRepository, movie_repository
from app.modules.data_collection.interfaces.match_to_database_interface import IMatchToDatabase
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.utils.lazy_load import lazy

logger=getLogger(__name__)
class MatchToDatabaseService(IMatchToDatabase):
    def  __init__(self, movie_repo:MovieRepository):
        self.movie_repo = movie_repo
    @staticmethod
    async def combin(movie_data_source:MovieDataSourceResult,movie:Movie):
        if movie:
            movie_data_source.movie_info = lazy(movie)
            if movie.title:
                movie_data_source.title=lazy(movie.title)
            if movie.tmdb_infos and movie.tmdb_infos.id and movie.tmdb_infos.season_number :
                movie_data_source.tmdb_infos=lazy(movie.tmdb_infos)

            if movie.total_episodes :
                movie_data_source.total_episodes=lazy(movie.total_episodes)
            if movie.season:
                movie_data_source.season=lazy(movie.season)

            if movie.title_season:
                movie_data_source.title_season=lazy(movie.title_season)

            if movie.description:
                movie_data_source.description=lazy(movie.description)
            if movie.douban_id:
                movie_data_source.douban_id=lazy(movie.douban_id)
            if movie.year:
                movie_data_source.year=lazy(movie.year)
            if movie.movie_type:
                movie_data_source.movie_type=lazy(movie.movie_type)
            if movie.category:
                movie_data_source.category=lazy(movie.category)
            if movie.pic:
                movie_data_source.pic=lazy(movie.pic)
            if movie.original_title:
                movie_data_source.original_title=lazy(movie.original_title)
            if movie.pubdate:
                movie_data_source.pubdate=lazy(movie.pubdate)

            movie_data_source.episodes_info=lazy(movie.episodes_info)
        else:

            logger.debug(f'未在数据库匹配到:{await movie_data_source.title_season } |  {await movie_data_source.douban_id}')


    async def match(self,movie_data_results: List[MovieDataSourceResult]) -> List[MovieDataSourceResult]:

        for movie_data in movie_data_results:
            movie= await self.movie_repo.find_by_douban_id(await movie_data.douban_id)
            await MatchToDatabaseService.combin(movie_data,movie)

        return movie_data_results
match_to_database_service=MatchToDatabaseService(movie_repo=movie_repository)