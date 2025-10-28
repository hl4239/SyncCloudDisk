import asyncio

from logging import getLogger
from typing import  Tuple, Optional



from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.models import MovieType, TMDBInfos
import tmdbsimple as tmdb

from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.movie_service import movie_service

from app.utils.lazy_load import lazy

logger=getLogger(__name__)
class TMDBInfoProviderService:



    async def _fetch_infos(self,tmdb_id:int,season_number:int)->Tuple[str,str]:
        """
        不缓存
        :param id:
        :return:
        """
        # 查找特定季
        tv_season = tmdb.TV_Seasons(tv_id=tmdb_id, season_number=season_number)
        response = tv_season.info(language='zh-CN')




        logger.debug(f'tv_info response={response}')
        if response['episodes']:
            episodes_info = response['episodes']
            current_episodes_number=episodes_info[-1]['episode_number']

            return movie_service.number_to_current_episodes(0,is_finale=False),movie_service.number_to_total_episodes(current_episodes_number)

        raise Exception('episodes not found')


    async def get_total_episodes(self, movie_data: MovieDataSourceResult) ->  Optional[str]:
        tmdb_infos = await movie_data.tmdb_infos
        if tmdb_infos.id and (tmdb_infos.season_number is not None):
            _, total_episodes = await self._fetch_infos(tmdb_infos.id,tmdb_infos.season_number)
            logger.debug(f'get_total_episodes={total_episodes} title={await movie_data.title} tmdb_infos={tmdb_infos}')
            return total_episodes
        logger.debug(f'get_total_episodes={None} title={await movie_data.title} tmdb_infos={tmdb_infos}')
        return None
    @staticmethod
    def get_movie_poster_urls(movie_id):
        """获取电影海报URL列表"""
        # 获取配置信息
        if not movie_id:
            return None
        config = tmdb.Configuration()
        config.info()
        base_url = config.images['base_url']

        # 获取电影图片
        movie = tmdb.Movies(movie_id)
        movie.images()

        # 构建海报URL列表
        poster_urls = []
        for poster in movie.posters:
            url = f"{base_url}w500{poster['file_path']}"
            poster_urls.append(url)

        if poster_urls:
            return poster_urls[0]
        return None
    @staticmethod
    def get_tv_season_poster_urls(tv_id, season_number):
        """获取电视剧季度海报URL列表"""
        # 获取配置信息
        if not tv_id or season_number is None:
            return None
        config = tmdb.Configuration()
        config.info()
        base_url = config.images['base_url']

        # 获取电视剧季度图片
        tv_season = tmdb.TV_Seasons(tv_id, season_number)



        tv_season.images()
        print(tv_season)
        # 构建海报URL列表
        poster_urls = []
        if not tv_season.posters:
            tv_season=tmdb.TV(tv_id)
            tv_season.images()
            print(tv_season.posters)


        for poster in tv_season.posters:
            url = f"{base_url}w500{poster['file_path']}"
            poster_urls.append(url)
        if poster_urls:
            return poster_urls[0]
        return None
    async  def get_pic(self,movie_data_source:MovieDataSourceResult):
        """
        获取TV季度海报的完整URL链接
        """
        tmdb_infos = await movie_data_source.tmdb_infos
        if tmdb_infos:
            movie_type=await movie_data_source.movie_type
            if movie_type==MovieType.TV:
               return self.get_tv_season_poster_urls(tmdb_infos.id,tmdb_infos.season_number)
            elif movie_type==MovieType.MOVIE:
               return self.get_movie_poster_urls(tmdb_infos.id)
        return None
tmdb_infos_provider_service=TMDBInfoProviderService()

async def main():
    a= await tmdb_infos_provider_service.get_pic(MovieDataSourceResult(movie_type=lazy(MovieType.TV),tmdb_infos=lazy(TMDBInfos(id=232557,season_number=1))))
    print(a)
if __name__ == '__main__':
    tmdb.API_KEY=settings.TMDB_API_KEY
    setup_logging()
    asyncio.run(main())
