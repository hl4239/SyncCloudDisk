import asyncio
import json
from logging import getLogger
from typing import List, Tuple, Optional



from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.models import Movie, MovieType
from app.modules.data_collection.interfaces.total_episodes_provider_interface import ITotalEpisodesProvider
import tmdbsimple as tmdb

from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.movie_service import movie_service
from app.utils.cache import async_ttl_cache

logger=getLogger(__name__)
class TMDBEpisodesProviderService(ITotalEpisodesProvider):



    async def _fetch_infos(self,tmdb_id:int,season_number:int)->Tuple[str,str]:

        """
        不缓存
        :param id:
        :return:
        """
        # 查找特定季


        tv_season = tmdb.TV_Seasons(tv_id=tmdb_id, season_number=season_number)
        response = tv_season.info(language='zh-CN')
        tv_season.images()

        # 检查是否有海报数据
        if hasattr(tv_season, 'posters'):
            print(f"找到 {len(tv_season.posters)} 张海报")
            for poster in tv_season.posters:
                print(f"海报路径: {poster['file_path']}")
                print(f"宽高比: {poster['aspect_ratio']}")
                print(f"语言: {poster.get('iso_639_1', 'null')}")
                print("---")

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

    async  def get_complete_poster_urls(self,tv_id, season_number):
        """
        获取TV季度海报的完整URL链接
        """
        try:
            # 1. 获取配置信息
            config = tmdb.Configuration()
            config.info()

            # 2. 获取季度图片信息
            tv_seasons = tmdb.TV_Seasons(tv_id, season_number)
            tv_seasons.images()

            # 3. 构建完整URL
            complete_urls = []
            if hasattr(tv_seasons, 'posters') and hasattr(config, 'images'):
                base_url = config.images['base_url']
                # 可选择的尺寸：w92, w154, w185, w342, w500, w780, original
                size = 'w500'

                for poster in tv_seasons.posters:
                    file_path = poster['file_path']
                    # 按照TMDb文档格式组合URL
                    complete_url = f"{base_url}{size}{file_path}"
                    complete_urls.append({
                        'url': complete_url,
                        'aspect_ratio': poster['aspect_ratio'],
                        'language': poster.get('iso_639_1', 'null'),
                        'vote_average': poster.get('vote_average', 0),
                        'width': poster.get('width', 0),
                        'height': poster.get('height', 0)
                    })

            return complete_urls

        except Exception as e:
            print(f"获取完整链接失败: {e}")
            return []


tmdb_episodes_provider_service=TMDBEpisodesProviderService()

async def main():
    a= await tmdb_episodes_provider_service.get_complete_poster_urls(280945,0)
    print(a)
if __name__ == '__main__':
    tmdb.API_KEY=settings.TMDB_API_KEY
    setup_logging()
    asyncio.run(main())
