from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.database.models import Movie, MovieType
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult


class IMapper(ABC):

    @abstractmethod
    def map_to_movie(self,original:BaseModel)->Movie:
        """
        将某个数据模型转为movie
        :param original:
        :return:
        """

    @abstractmethod
    def map_to_movies(self,original:BaseModel)->list[Movie]:
        """
        将一组数据模型转为list movie
        :param original:
        :return:
        """
    @abstractmethod
    def map_to_movie_data_source(self,original:BaseModel)->MovieDataSourceResult:
        """

        :param original:
        :return:
        """

    @abstractmethod
    def map_to_movies_data_source(self, original: BaseModel) -> list[MovieDataSourceResult]:
        """

        :param original:
        :return:
        """

    @staticmethod
    def get_movie_type(douban_type):
        if douban_type == 'tv':
            return MovieType.TV
        elif douban_type == 'movie':
            return MovieType.MOVIE
        else:
            return MovieType.OTHER