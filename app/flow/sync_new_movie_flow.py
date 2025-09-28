
# prefect_flow_async.py
import asyncio
import logging
from datetime import datetime
from typing import List

import pytz
import tmdbsimple
from pydantic import BaseModel, Field
from pygments.lexer import default

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.task_registry import registry
from app.database.database import init_db
from app.database.models import Movie, TVCategory, MovieCategory, CloudShareLink, MovieType, MetaDataProvider
from app.database.movie_repository import movie_repository
from app.modules.data_collection.flow import data_collection_get_hot_flow, search,  \
    get_movies_by_douban_id
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.filter.flow import title_and_episode_filter_flow, full_episode_filter_flow
from app.modules.filter.schemas import TargetEpisodeFilterResult
from app.modules.link_parse.flow import link_parse_flow_parses
from app.modules.link_parse.schemas import LinkParseResult, PrepareParseLinks
from app.modules.link_scraping.flow import link_scrape_flow_search
from app.modules.link_scraping.schemes.link import LinkScrapeResult
from app.modules.new_movie_metadata_collector.services.ren_ren_provider_service import renren_new_movie_provider_service
from app.modules.storage_operations.flow import save_to_cloud_flow
from app.services.movie_service import movie_service
logger=logging.getLogger(__name__)

# @task
async def collect_data_hot(categories:List[TVCategory],count=1)->List[MovieDataSourceResult]:
    return await data_collection_get_hot_flow(categories,count)

# @task
async def adapt_to_movies(movie_data_source:List[MovieDataSourceResult])->List[Movie]:
    ...
# @task
async def link_scraping(movies:List[Movie],count:int)->List[LinkScrapeResult]:
    results= await link_scrape_flow_search(movies,count)
    return results
# @task
async def link_parse(link_scrape_datas:List[PrepareParseLinks])->List[LinkParseResult]:
    results= await link_parse_flow_parses(link_scrape_datas)
    return results



# @task
async def combin_to_movies(movie_datas_sources:List[MovieDataSourceResult])->List[Movie]:
    return await movie_service.combin_to_movies(movie_datas_sources)



# @task
async def save_to_database(movies:List[Movie]):
    await movie_repository.upsert(movies,ignore_none=True)

async def save_to_cloud(target_episode_results: List[TargetEpisodeFilterResult])->List[Movie]:
    return  await save_to_cloud_flow(target_episode_results)

async def save_new_movies_metadata_to_database(new_movies:List[MetaDataProvider])->List[Movie]:
    movies=[]
    total=[]
    for new_movie in new_movies:
        r=await movie_repository.find_by_metadata_provider(new_movie.provider,new_movie.title,new_movie.id)
        if not r:
            r=  await Movie.find_one(Movie.title_season==new_movie.title)
        if not r:
            search_r = await search(new_movie.title)
            douban_id = search_r[0].douban_id
            movie_type = search_r[0].movie_type

        else:
            douban_id=r.douban_id
            movie_type=r.movie_type
        total.append({
            'douban_id':douban_id,
            'movie_type':movie_type,
            'provider': new_movie,
        })

    movies_source=await get_movies_by_douban_id(params=[(i['douban_id'],i['movie_type'])for i in total])
    movies=await combin_to_movies(movies_source)
    douban_id_maps={
        i['douban_id']:i['provider'] for i in total
    }
    for movie in movies:
        _is_find = False
        for p in movie.metadata_providers:
            if p.provider==douban_id_maps[movie.douban_id].provider :
                p=douban_id_maps[movie.douban_id]
                break
        if not _is_find :
            movie.metadata_providers.append(douban_id_maps[movie.douban_id])
    await save_to_database(movies)
    return movies



# 另一个任务示例：数据处理（参数模型不同）
class HotCollectParams(BaseModel):
    categories:List[TVCategory|MovieCategory]=Field(default=[TVCategory.CHINA],description='''China
    Japan
    Korea
    Europe
    Animation
    ''')
    count:int=Field(default=5,description='每个category采集个数')
@registry.register(name="豆瓣热门影视采集", params_model=HotCollectParams)
async def flow1(params: HotCollectParams, progress_callback, log_callback):
    movie_data_source_results=  await collect_data_hot(params.categories,count=params.count)
    logger.info(f'采集到{len(movie_data_source_results)}个影视')
    movies=await combin_to_movies(movie_data_source_results)
    await save_to_database(movies)
    progress_callback(100)
    return [
        movie.title_season for movie in movies
    ]




class P1(BaseModel):
    scrape_count:int=Field(default=3,description='每个影视爬取的网盘分享链接个数')
    skip_not_latest_episode:bool=Field(default=True,description='是否跳过未达到最新剧集的分享链接')
    is_force:bool=Field(default=False,description='是否强制更新未到时间点的影视')
    ...
@registry.register(name="同步今日可更新影视资源到网盘", params_model=P1)
async def flow2(params:P1, progress_callback, log_callback):
    today_movies=await movie_repository.find_movies_with_episode_today()
    to_save_movies=[]
    now=datetime.now(pytz.timezone("Asia/Shanghai"))
    if not params.is_force:
        for movie in today_movies:
            today_episodes=movie.get_today_will_update_episodes()
            max_episode=max(today_episodes,key=lambda episode:episode.episode_number)
            if max_episode.full_air_datetime<now:
                to_save_movies.append(movie)
    else:
        to_save_movies=today_movies

    logger.info(f'今日已到更新时间点的movie:{[i.title_season for i in to_save_movies]}')

    progress_callback(20)
    scrape_result=await link_scraping(to_save_movies,count=params.scrape_count)
    progress_callback(50)


    link_parse_results=await link_parse([PrepareParseLinks(scrape_quark_links=i.quark_links,links=[CloudShareLink(url=j,title=i.movie.title_season)for j in i.movie.share_links],movie=i.movie) for i in scrape_result])

    filter_result=await title_and_episode_filter_flow(link_parse_results)
    if params.skip_not_latest_episode:
        filter_result=await full_episode_filter_flow(filter_result)

    result=await save_to_cloud(filter_result)
    await save_to_database(result)
    progress_callback(100)
    return result


class P2(BaseModel):
    key:str=Field(default='鬼吹灯',description='关键词')
@registry.register(name="从豆瓣搜索", params_model=P2)
async def search_douban(params:P2,progress_callback, log_callback):

    r=await search(params.key)
    progress_callback(100)
    return r

class P3(BaseModel):
    douban_ids:List[str]=Field(default=None,description='douban_id')
    movie_type:MovieType=Field(default=None,description='tv 或 movie')
    is_sync_to_cloud:bool=Field(default=False,description='是否同时同步资源到网盘')
    scrape_count: int = Field(default=3, description='每个影视爬取的网盘分享链接个数')
    skip_not_latest_episode: bool = Field(default=True, description='是否跳过未达到最新剧集的分享链接')
@registry.register(name="根据douban_id保存影视元数据", params_model=P3)
async def get_by_douban_ids(params:P3,progress_callback, log_callback):
    douban_ids=params.douban_ids
    movie_type=params.movie_type
    is_sync_to_cloud=params.is_sync_to_cloud

    r=await get_movies_by_douban_id(douban_ids=douban_ids,movie_type=movie_type)
    progress_callback(30)
    movies = await combin_to_movies(r)
    progress_callback(50)
    await save_to_database(movies)
    progress_callback(60)
    logger.info(f'根据{douban_ids}已将该影视元数据入库{movies}')
    if not is_sync_to_cloud:
        progress_callback(100)
        return [
            movie.title_season for movie in movies
        ]
    else:
        progress_callback(70)
        scrape_result = await link_scraping(movies, count=params.scrape_count)
        progress_callback(80)

        link_parse_results = await link_parse([PrepareParseLinks(scrape_quark_links=i.quark_links, links=[
            CloudShareLink(url=j, title=i.movie.title_season) for j in i.movie.share_links], movie=i.movie) for i in
                                               scrape_result])

        filter_result = await title_and_episode_filter_flow(link_parse_results)
        if params.skip_not_latest_episode:
            filter_result = await full_episode_filter_flow(filter_result)

        result = await save_to_cloud(filter_result)
        await save_to_database(result)
        progress_callback(100)
        return result



class P4(BaseModel):
    is_sync_to_cloud: bool = Field(default=False, description='是否同时同步资源到网盘')
@registry.register(name="获取今日新的影视，从人人视频抓取", params_model=P4)
async def get_today_new_movie_metadata(params:P4,progress_callback, log_callback):
    new_movies= await renren_new_movie_provider_service.get_today_new_movie_metadata()
    search_results=[]
    print(new_movies)
    return new_movies






async def main():
    await init_db()
    setup_logging()
    tmdbsimple.API_KEY = settings.TMDB_API_KEY

    result=    await get_today_new_movie_metadata(None,None,None)
    await  save_new_movies_metadata_to_database(result)
    print(result)
if __name__ == '__main__':
    asyncio.run(main())
