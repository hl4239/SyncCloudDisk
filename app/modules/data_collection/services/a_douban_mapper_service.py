import re
from datetime import datetime
from typing import List, Tuple, Optional, Union

from pydantic import BaseModel

from app.database.models import Movie, MovieType,  MovieCategory
from app.modules.data_collection.schemas.douban_schemas import DoubanDetailResponse, DoubanDetailLazyResponse
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.utils.lazy_load import lazy, Lazy


class DoubanMapperService1:

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


    async def _get_movie_category(self, douban_item: DoubanDetailLazyResponse) -> MovieCategory:
        movie_type =await self._get_movie_type(douban_item.subtype)
        countries =await douban_item.countries
        first_country = countries[0]
        print(first_country)
        if any(kw == first_country for kw in ['中国', '中国大陆', '大陆','中国香港']):
            return MovieCategory.CHINA
        elif any(kw == first_country for kw in  ['美国',
                    "英国", "法国", "德国", "意大利", "西班牙", "葡萄牙",
                    "荷兰", "比利时", "卢森堡", "瑞士", "奥地利", "爱尔兰",
                    "挪威", "瑞典", "芬兰", "丹麦", "冰岛",
                    "希腊", "塞浦路斯", "马耳他",
                    "波兰", "捷克", "斯洛伐克", "匈牙利",
                    "罗马尼亚", "保加利亚", "克罗地亚", "斯洛文尼亚",
                    "塞尔维亚", "黑山", "北马其顿", "阿尔巴尼亚", "科索沃",
                    "爱沙尼亚", "拉脱维亚", "立陶宛",
                    "白俄罗斯", "乌克兰", "摩尔多瓦"
                ]
                ):
            return MovieCategory.EUROPE
        elif any(kw == first_country for kw in ['韩国']):
            return MovieCategory.KOREA
        elif any(kw == first_country for kw in ['日本']):
            return MovieCategory.JAPAN
        else:
            return MovieCategory.OTHER


    async def get_total_episodes(self,episodes_count):
        return f'{await episodes_count}集全'

    async def get_pic(self,pic):
        return (await pic).large

    async def get_date(self,date:Lazy[ List[str]]):
        date_str=(await date)[0]
        # 去掉括号和里面的内容
        clean_date = date_str.split("(")[0]

        # 转换为 datetime 对象
        dt = datetime.strptime(clean_date, "%Y-%m-%d").date()
        return dt



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
        movie_data_source.pubdate = lazy(lambda :self.get_date(original.pubdate))
        return movie_data_source


douban_mapper_service_1=DoubanMapperService1()
