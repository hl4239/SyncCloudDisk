import asyncio
import datetime
from typing import  Optional, Tuple

from charset_normalizer.md import getLogger

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.models import MovieType
from app.modules.data_collection.interfaces.tmdb_id_provider_interface import ITMDBIDProvider

from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
import tmdbsimple as tmdb



logger=getLogger(__name__)
class ATMDBIDProviderService(ITMDBIDProvider):
    def __init__(self):
        ...
    @classmethod
    async def get_id_1(cls,title_season:str,movie_type:MovieType,year:Optional[str]=None)->Optional[Tuple[Optional[int],Optional[int]]] :
        """
        根据title_season 和year搜索 如果存在多个一样的结果，则需手动干预，如果第一个结果不一样则无效
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
            r1=None
            r2=None
            if movie_type == MovieType.TV:
                r1 = response['results'][0]['name']
            else:
                r1 = response['results'][0]['title']
            if len(response['results'])>1:
                if movie_type==MovieType.TV:
                    r2=response['results'][1]['name']
                else:
                    r2=response['results'][1]['title']
                if r1==r2:
                    logger.warning(f'存在多个与title_season相同的搜索结果无法确定,需人工干预  title_season={title_season},movie_type={movie_type},year={year}')
                    return None

            if r1==title_season:
                tv_id = response['results'][0]['id']
                if movie_type==MovieType.TV:
                    tv = tmdb.TV(tv_id)
                    tv_info = tv.info(language='zh-CN')
                    if 'seasons' not in tv_info:
                        logger.warning(f'未找到seasons信息 title_season={title_season} movie_type={movie_type} year={year} tv_id={tv_id} tv_info:{tv_info}')
                        return None
                    target_season = None
                    season_info=tv_info['seasons'][0]
                    logger.debug(
                        f'title_season={title_season} year={year} movie_type={movie_type} tmdb_id={tv_id} season_number={season_info['season_number']}')
                    return tv_id, season_info['season_number']
                return tv_id,None



        logger.warning(f'未匹配到与title_season的tmdb_id和season，title_season={title_season},movie_type={movie_type},year={year}')
        return None



    @classmethod
    async def _get_id(cls,title_season:str,movie_type:MovieType,year:Optional[str]=None,is_original_title=False)->Optional[Tuple[Optional[int],Optional[int]]] :
        """
              根据title_season 和year搜索 如果存在多个一样的结果，则需手动干预，如果第一个结果不一样则无效
              :param title_season:
              :param year:
              :param movie_type:
              :return:
              """
        response = None
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
        tv_title='name'
        movie_title='title'
        if is_original_title:
            tv_title='original_name'
            movie_title='original_title'
        logger.debug(
            f'调用tmdb_api参数：title_season={title_season},movie_type={movie_type},year={year} | 响应：{response}')
        if response and len(response['results']) > 0:
            r1 = None
            r2 = None
            if movie_type == MovieType.TV:

                r1 = (response['results'][0][tv_title], datetime.datetime.strptime(response['results'][0]['first_air_date'], "%Y-%m-%d").year,response['results'][0]['id'])
            else:
                r1 = (response['results'][0][movie_title], datetime.datetime.strptime(response['results'][0]['release_date'], "%Y-%m-%d").year,response['results'][0]['id'])
            if len(response['results']) > 1:
                if movie_type == MovieType.TV:
                    r2 = (response['results'][1][tv_title], datetime.datetime.strptime(response['results'][1]['first_air_date'], "%Y-%m-%d").year,response['results'][0]['id'])
                else:
                    r2 =  (response['results'][1][movie_title], datetime.datetime.strptime(response['results'][1]['release_date'], "%Y-%m-%d").year,response['results'][0]['id'])
                if r1[:2] == r2[:2]:
                    logger.warning(
                        f'存在多个与title_season相同的搜索结果无法确定,需人工干预  title_season={title_season},movie_type={movie_type},year={year}')
                    return None
            if r1[:2] == (title_season,int(year)):
                tv_id = r1[2]
                if movie_type == MovieType.TV:
                    tv = tmdb.TV(tv_id)

                    tv_info = tv.info(language='zh-CN')
                    print(tv_info)
                    if 'seasons' not in tv_info:
                        logger.warning(
                            f'未找到seasons信息 title_season={title_season} movie_type={movie_type} year={year} tv_id={tv_id} tv_info:{tv_info}')
                        return None
                    target_season = None
                    season_info = tv_info['seasons'][0]
                    logger.debug(
                        f'title_season={title_season} year={year} movie_type={movie_type} tmdb_id={tv_id} season_number={season_info['season_number']}')
                    return tv_id, season_info['season_number']
                return tv_id, None

        logger.warning(
            f'未匹配到与title_season的tmdb_id和season，title_season={title_season},movie_type={movie_type},year={year}')
        return None


    async def get_tmdb_id(self, movie_data_source: MovieDataSourceResult) -> Tuple[int, int]:
        ...
        """
        根据title_season 和年份 搜索

        :param movie_data_source:
        :return:
        """

        tmdb_id= await self._get_id(title_season=await movie_data_source.title_season, year=await movie_data_source.year,movie_type=await movie_data_source.movie_type)
        if  not tmdb_id:
            if await  movie_data_source.original_title_season:
                tmdb_id=await self._get_id(title_season=await movie_data_source.original_title_season, year=await movie_data_source.year,movie_type=await movie_data_source.movie_type,is_original_title=True)
        if not tmdb_id:
            logger.info(f'未搜索到"{await movie_data_source.title_season}的tmdb_id"')
        return tmdb_id


a_tmdb_id_provider_service=ATMDBIDProviderService()
async def main():
    tasks=[]
    setup_logging()
    tmdb.API_KEY=settings.TMDB_API_KEY
    print(await ATMDBIDProviderService._get_id(title_season='凡人修仙传',movie_type=MovieType.TV,year='2025'))
    # await asyncio.gather(*tasks)
if __name__ == '__main__':
    asyncio.run(main())