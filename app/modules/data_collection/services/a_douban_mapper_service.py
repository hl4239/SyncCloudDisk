import re
from typing import List, Tuple, Optional, Union

from pydantic import BaseModel

from app.database.models import Movie, MovieType, TVCategory, MovieCategory
from app.modules.data_collection.interfaces.mapper_interface import IMapper
from app.modules.data_collection.schemas.douban_schemas import DoubanDetailResponse, DoubanDetailLazyResponse
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.utils.lazy_load import lazy


class DoubanMapperService1(IMapper):

    def map_to_movie(self, original: BaseModel) -> Movie:
        pass

    def map_to_movies(self, original: BaseModel) -> list[Movie]:
        pass

    def map_to_movies_data_source(self, original: BaseModel) -> list[MovieDataSourceResult]:
        pass
    @classmethod
    async def _get_movie_type(cls,type_)->MovieType:
        douban_type=await type_
        return cls.get_movie_type(douban_type)


    async def _get_movie_category(self, douban_item: DoubanDetailLazyResponse) -> Union[MovieCategory, TVCategory]:
        movie_type =await self._get_movie_type(douban_item.subtype)
        countries =await douban_item.countries
        first_country = countries[0]
        print(first_country)
        if movie_type == MovieType.TV:
            if any(kw == first_country for kw in ['中国', '中国大陆', '大陆']):
                return TVCategory.CHINA
            elif any(kw == first_country for kw in ['英国', '美国']):
                return TVCategory.EUROPE
            elif any(kw == first_country for kw in ['韩国']):
                return TVCategory.KOREA
            elif any(kw == first_country for kw in ['日本']):
                return TVCategory.JAPAN
            else:
                return TVCategory.OTHER
        elif movie_type == MovieType.MOVIE:
            return MovieCategory.ALL
        else:
            return TVCategory.OTHER


    async def get_total_episodes(self,episodes_count):
        return f'{await episodes_count}集全'

    async def get_pic(self,pic):
        return (await pic).large



    def map_to_movie_data_source(self,original: DoubanDetailLazyResponse) -> MovieDataSourceResult:
        douban_id =original.id
        year =original.year
        description =original.intro
        tv_type = lazy(lambda :self._get_movie_type(original.subtype))
        title_season =original.title
        tv_category = lazy(lambda :self._get_movie_category(original))
        total_episodes = lazy(lambda :self. get_total_episodes(original.episodes_count))
        pic=lazy(lambda :self.get_pic(original.pic))
        movie_data_source = MovieDataSourceResult()
        movie_data_source.douban_id = douban_id
        movie_data_source.year = year
        movie_data_source.description = description
        movie_data_source.movie_type = tv_type
        movie_data_source.title_season = title_season
        movie_data_source.category = tv_category
        movie_data_source.total_episodes = total_episodes
        movie_data_source.pic=pic
        movie_data_source.original_title = lazy(original.original_title)
        return movie_data_source


douban_mapper_service_1=DoubanMapperService1()
