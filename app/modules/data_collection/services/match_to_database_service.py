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
            if movie.tmdb_infos:
                movie_data_source.tmdb_infos=lazy(movie.tmdb_infos)

            if movie.current_episodes and (await movie_data_source.current_episodes is None):
                movie_data_source.current_episodes=lazy(movie.current_episodes)
            if movie_data_source.total_episodes and (await movie_data_source.total_episodes is None):
                movie_data_source.total_episodes=lazy(movie_data_source.total_episodes)
            if movie.season:
                movie_data_source.season=lazy(movie.season)
        else:
            logger.debug(f'未在数据库匹配到:{await movie_data_source.title_season } |  {await movie_data_source.douban_id}')


    async def match(self,movie_data_results: List[MovieDataSourceResult]) -> List[MovieDataSourceResult]:

        for movie_data in movie_data_results:
            movie= await self.movie_repo.find_by_douban_id(await movie_data.douban_id)
            await MatchToDatabaseService.combin(movie_data,movie)

        return movie_data_results
match_to_database_service=MatchToDatabaseService(movie_repo=movie_repository)