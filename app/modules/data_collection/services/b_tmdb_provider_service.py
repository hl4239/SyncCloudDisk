import asyncio
import json
import logging
import re
from typing import  Tuple

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.models import MovieType
from app.modules.data_collection.interfaces.tmdb_id_provider_interface import ITMDBIDProvider, TMDBIDNotFound, \
    TMDBIDNotEnsure
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
import tmdbsimple as tmdb

from app.services.movie_service import MovieService
from app.utils.cache import async_ttl_cache

logger=logging.getLogger(__name__)
class BTMDBIDProviderService(ITMDBIDProvider):

    @staticmethod
    async def _fetch_tmdb_id(title:str,season:str,movie_type:MovieType)->Tuple[int,int]:
        """
        根据标题、season查找电视剧
        当season未第xx季时，如果存在多个相同的title则转人工干预，否则对第一个结果寻找相同的season
        当season为特殊名时，对比所有相同的title直到找到相同的season

        Args:
            title: 电视剧标题
        Returns:
            包含电视剧和季信息的字典
        """
        # 第一步：搜索电视剧
        if not title or not season:
            raise TMDBIDNotFound(f'title或者season为空：title={title} season={season}')

        search = tmdb.Search()
        response=None
        if movie_type == MovieType.TV:
            response = search.tv(
                query=title,
                language='zh-CN',
                include_adult=False
            )

        if movie_type == MovieType.MOVIE:
            response = search.movie(
                query=title,
                language='zh-CN',
                include_adult=False
            )
        if not search.results or search.results[0]['name']!=title:
            raise TMDBIDNotFound(f'未搜索到任何内容或与搜索结果title不同，参数：title={title},season={season}  搜索结果：{search.results[0]['name']}')
        # 正则：标准“第X季”

        normal_season_pattern = re.compile(r"^第\d+季$")
        if  normal_season_pattern.match(season):
            if len(search.results)>1:
                result_1_title=search.results[0]['name']
                result_2_title=search.results[1]['name']
                if result_1_title==result_2_title:
                    raise TMDBIDNotEnsure(f'season为"第x季"格式，且搜索结果title存在多个相同无法确定需人工干预')
            else:
                tv_id=search.results[0]['id']
                tv = tmdb.TV(tv_id)
                tv_info = tv.info(language='zh-CN')
                if 'seasons' not in tv_info:
                    raise TMDBIDNotFound(f'未找到seasons信息 title:{title} season={season} tv_id={tv_id} tv_info:{tv_info}')
                target_season = None
                for season_info in tv_info['seasons']:
                    if season_info['name'].lower()==season.lower():
                        logger.debug(f'title={title} season={season} tmdb_id={tv_id} season_number={season_info['season_number']}')
                        return tv_id, season_info['season_number']
        else:
            for result in search.results:
                tv_id = result['id']
                tv = tmdb.TV(tv_id)
                tv_info = tv.info(language='zh-CN')
                if 'seasons' not in tv_info:
                    raise TMDBIDNotFound(
                        f'未找到seasons信息 title:{title} season={season} tv_id={tv_id} tv_info:{tv_info}')
                target_season = None
                for season_info in tv_info['seasons']:
                    if season_info['name'].lower() == season.lower():
                        logger.debug(
                            f'title={title} season={season} tmdb_id={tv_id} season_number={season_info['season_number']}')
                        return tv_id, season_info['season_number']
        raise TMDBIDNotFound(f'未找到tmdb_id和season_number title:{title} season={season}')

    async def get_tmdb_id(self, movie_data_source: MovieDataSourceResult) -> Tuple[int, int]:
        ...
        """
        根据title season year获取
        :param movie_data_source:
        :return:
        """
        tmdb_id,season_number=await self._fetch_tmdb_id(await movie_data_source.title,MovieService.douban_season_to_tmdb_season(await movie_data_source.season),await movie_data_source.movie_type)
        return tmdb_id,season_number



b_tmdb_provider_service=BTMDBIDProviderService()

async def main():
    tmdb.API_KEY=settings.TMDB_API_KEY
    setup_logging()
    id,season_number= await b_tmdb_provider_service._fetch_tmdb_id('清潭国际高中','第 1 季')
    print(id,season_number)
if __name__ == '__main__':
    asyncio.run(main())
