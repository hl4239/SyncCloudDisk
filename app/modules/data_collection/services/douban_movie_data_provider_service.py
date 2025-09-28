import asyncio
import logging
from typing import Union, List, override

from watchfiles import awatch

from app.core.logging_config import setup_logging
from app.database.models import TVCategory, MovieCategory, Movie, MovieType
from app.modules.data_collection.clients.douban_client import get_douban_client, DoubanClient
from app.modules.data_collection.interfaces.mapper_interface import IMapper
from app.modules.data_collection.interfaces.movie_base_provider_interface import IMovieBaseProvider
from app.modules.data_collection.schemas.douban_schemas import DoubanDetailLazyResponse, DoubanSearchItem
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.utils.lazy_load import lazy
from app.modules.data_collection.services.a_douban_mapper_service import douban_mapper_service_1

logger=logging.getLogger(__name__)
class DoubanMovieBaseProviderService(IMovieBaseProvider):



    def __init__(self, douban_client:DoubanClient,mapper:IMapper):
        self.douban_client = douban_client
        self.mapper = mapper

    async def search(self,keyword:str,count=10):
        """
        count无效，始终根据豆瓣的接口返回多少搜索结果
        :param keyword:
        :param count:
        :return:
        """
        result= await self.douban_client.search(keyword)
        try:
            r=[]

            for i in result['subjects']['items']:
                if i['layout']=='subject':
                    print(i)
                    movie_type=douban_mapper_service_1.get_movie_type( i['target_type'])
                    title=i['target']['title']
                    year=i['target']['year']
                    pic=i['target']['cover_url']
                    douban_id=i['target_id']
                    r.append(DoubanSearchItem(title=title,douban_id=douban_id,pic=pic,movie_type=movie_type,year=year))
            return r


        except KeyError as e:
            logger.error(e,exc_info=True)
            return []

    async def detail(self,douban_id,movie_type):

        r= await self.douban_client.detail(douban_id, movie_type)
        logger.debug(f'抓取豆瓣影视详细信息：{douban_id} | {movie_type}结果： {r}')
        return r

    async def get_movie_by_douban_id(self, douban_id: str,movie_type:MovieType) -> List[MovieDataSourceResult]:
        lazy_result=lazy(lambda :self.detail(douban_id,movie_type))

        l=DoubanDetailLazyResponse(id=lazy(douban_id),
                                   title=lazy_result.title,
                                   subtype=lazy_result.subtype,
                                   pic=lazy_result.pic,
                                   year=lazy_result.year,
                                   episodes_count=lazy_result.episodes_count,
                                   card_subtitle=lazy_result.card_subtitle,
                                   countries=lazy_result.countries,
                                   intro=lazy_result.intro,
                                   original_title=lazy_result.original_title,)
        return[self.mapper.map_to_movie_data_source(l)]


    @override
    async def get_hot_movies(self, categories: Union[List[TVCategory] | List[MovieCategory]], count: int = 10) -> List[MovieDataSourceResult]:

        tasks=[]
        for category in categories:
            tasks.append(self.douban_client.get_hot_tv(category,count))
        resp= await asyncio.gather(*tasks)



        result=[]
        for r in resp:
            for i in r.subject_collection_items:
                l=await self.get_movie_by_douban_id(i.id,self.mapper.get_movie_type(i.type))
                result.extend(l)
        return result
_douban_movie_base_provider_service = None
async def get_douban_movie_base_provider_service():
    global _douban_movie_base_provider_service
    if _douban_movie_base_provider_service is None:
        douban_client = await get_douban_client()
        _douban_movie_base_provider_service=DoubanMovieBaseProviderService(douban_client=douban_client,mapper=douban_mapper_service_1)
    return _douban_movie_base_provider_service

async def main():
    setup_logging()
    d=await get_douban_movie_base_provider_service()
    r=  await d.get_movie_by_douban_id('36331163',MovieType.TV)
    r0=r[0]
    print(
        await r0.douban_id,
        await r0.title_season,
        await r0.subtitle,
        await r0.pic,
        await r0.description,
        await r0.year,
        await r0.category,
        await r0.movie_type,
        await r0.total_episodes,
        await r0.original_title
    )


if __name__ == '__main__':
    asyncio.run(main())
