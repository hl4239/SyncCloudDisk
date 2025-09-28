from abc import ABC, abstractmethod
from typing import List, Union

from app.database.models import TVCategory, Movie, MovieCategory, MovieType
from app.modules.data_collection.schemas.douban_schemas import DoubanDetailResponse
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult


class IMovieBaseProvider(ABC):
    """
    获取影视基本元数据
    """

    @abstractmethod
    async def get_hot_movies(self,category:Union[List[TVCategory]|List[MovieCategory]] ,count:int=10) -> List[MovieDataSourceResult]:
        """
        根据tv_category获取热门资源
        :param count:
        :param category:
        :return:
        """
        ...

    @abstractmethod
    async def search(self,keyword:str,count=10):
        """
        根据关键词搜索，只返回匹配到的前count个数据
        :param count:
        :param keyword:
        :return:
        """
        ...

    async def get_movie_by_douban_id(self, douban_id: str, movie_type: MovieType) -> List[MovieDataSourceResult]:
       ...