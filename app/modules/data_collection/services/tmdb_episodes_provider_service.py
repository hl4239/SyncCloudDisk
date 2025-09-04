import json

from openai import responses

from app.core.config import settings
from app.database.models import Movie, MovieType
from app.modules.data_collection.interfaces.current_episodes_provider_interface import ICurrentEpisodesProvider
from app.modules.data_collection.interfaces.total_episodes_provider_interface import ITotalEpisodesProvider
import tmdbsimple as tmdb

from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.utils.cache import async_ttl_cache


class TMDBEpisodesProviderService(ICurrentEpisodesProvider,ITotalEpisodesProvider):
    def __init__(self):
        self. tmdb=tmdb

        tmdb.API_KEY = settings.TMDB_API_KEY
        self.language='zh-CN'

    @async_ttl_cache(ttl=10)
    async def _fetch_infos(self,id:str):
        """
        缓存10秒
        :param id:
        :return:
        """
        ...

    async def get_total_episodes(self, movie: MovieDataSourceResult) -> str|None:

        movie_type=await movie.movie_type
        tmdb_infos=await movie.tmdb_infos
        if movie_type==MovieType.MOVIE:
            return None

        if not tmdb_infos.id:
            return None

        ...




    async def get_current_episodes(self, movie: Movie) -> str|None:
        movie_type = await movie.movie_type
        tmdb_infos = await movie.tmdb_infos
        if movie_type == MovieType.MOVIE:
            return None

        if not tmdb_infos.id:
            return None
        ...

# tmdb.API_KEY=settings.TMDB_API_KEY
# # 获取今天播出的剧集
# tv_general = tmdb.TV()
# response = tv_general.airing_today(language='zh-CN')
# print(json.dumps(response, indent=4, ensure_ascii=False))
# for show in tv_general.results:
#     if show['name'] == '目标剧集名':
#         print(f"今天播出: {show['name']}")
#