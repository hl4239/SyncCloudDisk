from abc import ABC, abstractmethod
from typing import List

from app.database.models import Movie
from app.database.movie_repository import MovieRepository
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult


class IMatchToDatabase(ABC):

    @abstractmethod
    async def match(self, movie_data_results: List[MovieDataSourceResult]) -> List[MovieDataSourceResult]:
        """
        匹配数据库存在的，并合并数据库现有的字段到MovieDataSourceResult
        :param movie_data_results:
        :return:
        """
        ...