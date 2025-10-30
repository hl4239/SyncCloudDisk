import asyncio
from logging import getLogger
from typing import List, Tuple

import tmdbsimple


from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.task_manager import task_manager
from app.database.database import init_db
from app.database.models import MovieType, MovieCategory
from app.database.movie_repository import movie_repository

from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.data_collection.services.ai_copilot_episodes_info_provider_service import \
    ai_copilot_episodes_air_time_provider
from app.modules.data_collection.services.douban_movie_data_provider_service import \
    get_douban_movie_base_provider_service
from app.modules.data_collection.services.fallback_split_title_season_service import \
     fallback_split_title_season_service
from app.modules.data_collection.services.fallback_tmdb_id_provider_service import fallback_tmdb_id_provider_service

from app.modules.data_collection.services.tmdb_air_date_provider_service import tmdb_air_date_provider
from app.modules.data_collection.services.tmdb_info_provider_service import  \
    tmdb_infos_provider_service
from app.services.movie_service import movie_service
from app.utils.lazy_load import lazy

logger=getLogger(__name__)
# @task(cache_policy=NO_CACHE)# @task(cache_policy=NO_CACHE)  # 或者 @task(cache_key_fn=task_input_hash)
# @task

async def search_from_douban(key):
    """
    从豆瓣搜索
    :param key:
    :return:
    """
    return await (await get_douban_movie_base_provider_service()).search(keyword=key)

async def get_douban_hot_movie_data_sources(categories: List[MovieCategory], count: int = 10):
    f=await (await get_douban_movie_base_provider_service()).get_hot_movies(categories, count)
    r=  await registry_movie_data_sources([(i.id,i.get_movie_type()) for i in f])
    return r
async def registry_movie_data_sources(douban_id_movie_types: List[Tuple[str, MovieType]]):
    all_title_seasons = []
    all_movie_data_sources=[]
    for douban_id, movie_type in douban_id_movie_types:

        movie = await movie_repository.find_by_douban_id(douban_id)
        movie_data_source = MovieDataSourceResult()

        douban_provider = await get_douban_movie_base_provider_service()
        douban_metadata_lazy = douban_provider.get_movie_by_douban_id(
            douban_id=douban_id,
            movie_type=movie_type
        )

        # movie_info
        if movie:
            movie_data_source.movie_info = lazy(movie)


        # tmdb_infos
        if movie and movie.tmdb_infos and movie.tmdb_infos.id :
            movie_data_source.tmdb_infos = lazy(movie.tmdb_infos)
        else:
            movie_data_source.tmdb_infos = lazy(
                lambda c=movie_data_source: fallback_tmdb_id_provider_service.get_tmdb_infos(c)
            )

        # total_episodes
        if movie and movie.total_episodes:
            movie_data_source.total_episodes = lazy(movie.total_episodes)
        else:
            movie_data_source.total_episodes = lazy(
                lambda c=douban_metadata_lazy: c.get_total_episodes()
            )


        # title_season
        if movie and movie.title_season:
            movie_data_source.title_season = lazy(movie.title_season)
        else:
            # 注意：原代码是直接赋 douban_metadata_lazy.title（可能本身就是 Lazy/属性访问）
            movie_data_source.title_season = douban_metadata_lazy.title


        # season
        if movie and movie.season :
            movie_data_source.season = lazy(movie.season)
        else:
            movie_data_source.season = lazy(
                lambda a=movie_data_source.title_season:
                    fallback_split_title_season_service.get_season(a, all_title_seasons)
            )

        # title
        if movie and movie.title :
            movie_data_source.title = lazy(movie.title)
        else:
            movie_data_source.title = lazy(
                lambda a=movie_data_source.title_season:
                    fallback_split_title_season_service.get_title(a, all_title_seasons)
            )

        # original_title_season
        if movie and movie.original_title_season is not None:
            movie_data_source.original_title_season = lazy(movie.original_title_season)
        else:
            movie_data_source.original_title_season = douban_metadata_lazy.original_title


        # original_title
        if movie and movie.original_title is not None :
            movie_data_source.original_title = lazy(movie.original_title)
        else:
            movie_data_source.original_title = lazy(
                lambda i=movie_data_source.original_title_season:
                    fallback_split_title_season_service.get_title(i, all_title_seasons)
            )


        # description
        if movie and movie.description:
            movie_data_source.description = lazy(movie.description)
        else:
            movie_data_source.description = douban_metadata_lazy.intro

        # douban_id
        movie_data_source.douban_id = lazy(douban_id)
        # year
        if movie and movie.year:
            movie_data_source.year = lazy(movie.year)
        else:
            movie_data_source.year = douban_metadata_lazy.year

        # movie_type
        movie_data_source.movie_type = lazy(movie_type)

        # category
        if movie and movie.category:
            movie_data_source.category = lazy(movie.category)
        else:
            movie_data_source.category = lazy(
                lambda c=douban_metadata_lazy: c.get_category()
            )

        # pic
        if movie and movie.pic:
            movie_data_source.pic = lazy(movie.pic)
        else:
            movie_data_source.pic = lazy(
                lambda a=movie_data_source: tmdb_infos_provider_service.get_pic(a)
            )

        # pubdate
        if movie and movie.pubdate:
            movie_data_source.pubdate = lazy(movie.pubdate)
        else:
            movie_data_source.pubdate = lazy(
                lambda c=douban_metadata_lazy: c.get_pubdate()
            )

        # episodes_info
        if movie and movie.episodes_info:
            movie_data_source.episodes_info = lazy(movie.episodes_info)
        else:
            movie_data_source.episodes_info = lazy(
                lambda a=movie_data_source.total_episodes:
                    movie_service.create_episodes_info(a)
            )

        # actors
        if movie and movie.actors:
            movie_data_source.actors = lazy(movie.actors)
        else:
            movie_data_source.actors = lazy(
                lambda c=douban_metadata_lazy: c.get_actors()
            )
        # aliases
        if movie and movie.aliases:
            movie_data_source.aliases = lazy(movie.aliases)
        else:
            movie_data_source.aliases = douban_metadata_lazy.aka

        # genres
        if movie and movie.genres:
            movie_data_source.genres = lazy(movie.genres)
        else:
            movie_data_source.genres = douban_metadata_lazy.genres


        # 补充外部 provider 的字段
        await tmdb_air_date_provider.set_air_date(movie_data_source)
        await ai_copilot_episodes_air_time_provider.set_air_time(movie_data_source)
        all_movie_data_sources.append(movie_data_source)
        all_title_seasons.append(movie_data_source.title_season)
        all_title_seasons.append(movie_data_source.original_title_season)
    return all_movie_data_sources

async def f1():
    movie_data_sources=await get_douban_hot_movie_data_sources(categories=[MovieCategory.CHINA],count=10)
    for movie_data_source in movie_data_sources:
        await movie_data_source.douban_id
        await movie_data_source.episodes_info
        await movie_data_source.pic
async def main():
    setup_logging()
    await init_db()
    tmdbsimple.API_KEY = settings.TMDB_API_KEY
    tasks=[f1() for i in range(3)]
    await asyncio.gather(*tasks)
    while True:
        await asyncio.sleep(60)




if __name__ == '__main__':
    asyncio.run(main())
