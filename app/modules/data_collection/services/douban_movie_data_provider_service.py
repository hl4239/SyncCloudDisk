import asyncio
from typing import Union, List, override

from app.database.models import TVCategory, MovieCategory, Movie
from app.modules.data_collection.clients.douban_client import get_douban_crawler
from app.modules.data_collection.interfaces.mapper_interface import IMapper
from app.modules.data_collection.interfaces.movie_base_provider_interface import IMovieBaseProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult


class DoubanMovieBaseProviderService(IMovieBaseProvider):

    def __init__(self, douban_client,mapper:IMapper):
        self.douban_client = douban_client
        self.mapper = mapper

    async def search(self, keyword: str, count=1) -> List[Movie]:
        pass

    @override
    async def get_hot_movies(self, categories: Union[List[TVCategory] | List[MovieCategory]], count: int = 10) -> List[MovieDataSourceResult]:

        tasks=[]
        for category in categories:
            tasks.append(self.douban_client.get_hot_tv(category,count))
        resp= await asyncio.gather(*tasks)
        result=[]
        for r in resp:
            l= self.mapper.map_to_movies_data_source(r)
            result.extend(l)
        return result
