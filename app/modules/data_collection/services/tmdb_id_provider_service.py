import asyncio
import copy
from typing import List, Optional

from charset_normalizer.md import getLogger

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.models import TMDBInfos, MovieType
from app.modules.data_collection.interfaces.movie_base_provider_interface import IMovieBaseProvider
from app.modules.data_collection.interfaces.tmdb_id_provider_interface import ITMDBIDProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
import tmdbsimple as tmdb

from app.utils.cache import async_ttl_cache
from app.utils.lazy_load import lazy

logger=getLogger(__name__)
class TMDBIDProviderService(ITMDBIDProvider):
    def __init__(self):
        ...
    @classmethod
    @async_ttl_cache(ttl=3600)
    async def get_id_1(cls,title_season:str,movie_type:MovieType,year:Optional[str]=None)->str|None:
        """
        根据title_season 和year搜索 并取结果的第一个
        :param title_season:
        :param year:
        :param movie_type:
        :return:
        """
        response=None
        search = tmdb.Search()
        if movie_type == MovieType.TV:
            response = search.tv(
                query=title_season,
                first_air_date_year=year,
                language='zh-CN',
                include_adult=False
            )

        if movie_type == MovieType.MOVIE:
            response = search.movie(
                query=title_season,
                first_air_date_year=year,
                language='zh-CN',
                include_adult=False
            )
        logger.debug(f'调用tmdb_api参数：title_season={title_season},movie_type={movie_type},year={year} | 响应：{response}')
        if response and len(response['results'])>0 :

            return response['results'][0]['id']

        return None

    @classmethod

    async def get_tmdb_id(cls,movie_data_source:MovieDataSourceResult)->str:
        """
        根据title_season 和年份 搜索

        :param movie_data_source:
        :return:
        """
        tmdb_id= await cls.get_id_1(title_season=await movie_data_source.title_season, year=await movie_data_source.year,movie_type=await movie_data_source.movie_type)
        if  not tmdb_id:
            logger.info(f'未搜索到"{await movie_data_source.title_season}的tmdb_id"')
        return tmdb_id
    @classmethod
    async def get_tmdb_infos(cls,movie_data_source:MovieDataSourceResult)->TMDBInfos:
        print(f'title_season={await movie_data_source.title_season}' )
        tmdb_infos = await movie_data_source.tmdb_infos
        if tmdb_infos:
            if tmdb_infos.id:
                return tmdb_infos
        else:
            tmdb_infos = TMDBInfos()
        tmdb_infos.id = await cls.get_tmdb_id(movie_data_source)
        return tmdb_infos

    @classmethod
    async def set_id(cls,movie_data_sources:List[MovieDataSourceResult]) -> List[MovieDataSourceResult]:
        for movie_data_source in movie_data_sources:
            cloned_model = copy.deepcopy(movie_data_source)
            logger.debug(f'cloned_model={cloned_model.title_season}')
            movie_data_source.tmdb_infos=lazy(lambda c=cloned_model :cls.get_tmdb_infos(c))

        return movie_data_sources

async def main():
    tasks=[]
    setup_logging()
    tmdb.API_KEY=settings.TMDB_API_KEY
    movie_data=MovieDataSourceResult()
    movie_data1=MovieDataSourceResult()

    movie_data.title_season=lazy('你好')
    movie_data.movie_type=lazy(MovieType.TV)
    movie_data1.title_season=lazy('你好1')
    movie_data1.movie_type=lazy(MovieType.MOVIE)

    await TMDBIDProviderService.set_id([movie_data,movie_data1])
    print(await movie_data.tmdb_infos)
    print(await movie_data1.tmdb_infos)
    # await asyncio.gather(*tasks)
if __name__ == '__main__':
    asyncio.run(main())