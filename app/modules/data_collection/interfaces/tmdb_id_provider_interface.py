from abc import ABC, abstractmethod
from typing import List

from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult


class ITMDBIDProvider(ABC):
    @staticmethod
    @abstractmethod
    async def set_id(movie_data_sources:List[MovieDataSourceResult])->List[MovieDataSourceResult]:
        """
        如果tmdb_id存在则忽略，否则调用tmdb api获取
        :param movie_data_sources:
        :return:
        """
        ...