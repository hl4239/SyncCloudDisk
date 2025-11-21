
# prefect_flow_async.py
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import pytz
import tmdbsimple
from beanie.odm.operators.find.comparison import In
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.task_registry import registry
from app.database.database import init_db
from app.database.models import Movie, MovieCategory, CloudShareLink, MovieType, MetaDataProvider
from app.database.movie_repository import movie_repository
from app.modules.data_collection.flow import get_douban_hot_movie_data_sources,\
    registry_movie_data_sources, search_from_douban
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.filter.flow import title_and_episode_filter_flow
from app.modules.filter.schemas import TargetEpisodeFilterResult
from app.modules.link_parse.flow import link_parse_flow_parses
from app.modules.link_parse.schemas import LinkParseResult, PrepareParseLinks
from app.modules.link_scraping.flow import link_scrape_flow_search
from app.modules.link_scraping.schemes.link import LinkScrapeResult
from app.modules.new_movie_metadata_collector.services.ren_ren_provider_service import renren_new_movie_provider_service
from app.modules.publish.services.share_link_publish import share_link_publish_service
from app.modules.risk_detect.flow import detect_risk_share
from app.modules.storage_operations.flow import save_to_cloud_flow, recreate_dir
from app.modules.storage_operations.services.handle_risk_file_service import handle_risk_file_service
from app.services.movie_service import movie_service
logger=logging.getLogger(__name__)
#lock
#互斥锁： 网盘保存 检测与处理风险 重建目录
lock1=asyncio.Lock()



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
        douban_id =None
        movie_type=None
        r=await movie_repository.find_by_metadata_provider(new_movie.provider,new_movie.title,new_movie.id)
        if not r:
            r=  await Movie.find_one(Movie.title_season==new_movie.title)
        if not r:
            search_r = await search_from_douban(new_movie.title)
            t_tup=(new_movie.title,new_movie.year,new_movie.movie_type)
            # 优先根据年份 类型 title进行匹配
            for i in search_r:
                s=(i.title,i.year,i.movie_type)
                if t_tup==s:
                    douban_id=i.douban_id
                    movie_type=i.movie_type
                    break
            # 否则选择豆瓣搜索的第一个
            if search_r:
                r0=search_r[0]
                douban_id=r0.douban_id
                movie_type=r0.movie_type


        else:
            douban_id=r.douban_id
            movie_type=r.movie_type
        if douban_id is None or movie_type is None:
            logger.info(f'未能从豆瓣中搜索到：{new_movie}')
            continue
        total.append({
            'douban_id':douban_id,
            'movie_type':movie_type,
            'provider': new_movie,
        })

    movies_source=await registry_movie_data_sources([(i['douban_id'],i['movie_type'])for i in total])
    movies=await combin_to_movies(movies_source)
    douban_id_maps={
        i['douban_id']:i['provider'] for i in total
    }
    for movie in movies:
        _is_find = False
        for p in movie.metadata_providers:
            if p.provider==douban_id_maps[movie.douban_id].provider :
                p=douban_id_maps[movie.douban_id]
                _is_find=True
                break
        if not _is_find :
            movie.metadata_providers.append(douban_id_maps[movie.douban_id])
    # await save_to_database(movies)
    return movies

async def sync_movies_to_cloud(movies:List[Movie], scrape_count:int,skip_not_latest_episode:bool,is_force:bool)->List[Movie]:
    """

    :param log_callback:
    :param progress_callback:
    :param movies:
    :param scrape_count: 每个影视爬取的网盘分享链接个数
    :param skip_not_latest_episode: 是否跳过未达到最新剧集的分享链接
    :param is_force: 是否强制更新未到时间点的影视
    :return:
    """
    ...

# 另一个任务示例：数据处理（参数模型不同）
class HotCollectParams(BaseModel):
    categories:List[MovieCategory]=Field(default=[MovieCategory.CHINA],description='''China
    Japan
    Korea
    Europe
    Animation
    ''')
    count:int=Field(default=5,description='每个category采集个数')
@registry.register(name="豆瓣热门影视采集", params_model=HotCollectParams)
async def flow1(params: HotCollectParams, progress_callback, log_callback):
    movie_data_source_results=  await get_douban_hot_movie_data_sources(params.categories,count=params.count)


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
    async with lock1:
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
        progress_callback(10)
        not_save_movies = [i for i in to_save_movies if not i.is_tmdb_infos_avaliable()]

        to_save_movies = [i for i in to_save_movies if i.is_tmdb_infos_avaliable()]
        logger.warning(f'这些movie由于tmdb_info为空无法同步：{not_save_movies}')

        progress_callback(20)
        scrape_result=await link_scraping(to_save_movies,count=params.scrape_count)
        progress_callback(50)


        link_parse_results=await link_parse([PrepareParseLinks(scrape_quark_links=i.quark_links,scrape_baidu_links=i.baidu_links,links=[CloudShareLink(url=j,title=i.movie.title_season)for j in i.movie.share_links],movie=i.movie) for i in scrape_result])

        filter_result=await title_and_episode_filter_flow(link_parse_results,params.skip_not_latest_episode)


        result=await save_to_cloud(filter_result)
        await save_to_database(result)
        progress_callback(100)
        return result

class P5(BaseModel):
    douban_ids:List[str]=Field(default=['312231'],description='豆瓣id')
    scrape_count: int = Field(default=3, description='每个影视爬取的网盘分享链接个数')
    skip_not_latest_episode:bool=Field(default=True,description='只爬取含有最新剧集的分享链接')
@registry.register(name="根据douban_ids同步网盘", params_model=P5)
async def flow3(params:P5, progress_callback, log_callback):
    async  with lock1:
        f_movies = await Movie.find(In(Movie.douban_id, params.douban_ids)).to_list()

        logger.info(f'开始同步{[i.title_season for i in f_movies]}')
        progress_callback(20)
        to_save_movies=[i for i in f_movies if i.is_tmdb_infos_avaliable()]
        not_save_movies=[i for i in f_movies if not i.is_tmdb_infos_avaliable()]
        logger.warning(f'这些movie由于tmdb_info为空无法同步：{not_save_movies}')
        progress_callback(30)
        scrape_result=await link_scraping(to_save_movies,count=params.scrape_count)
        progress_callback(50)


        link_parse_results=await link_parse([PrepareParseLinks(scrape_quark_links=i.quark_links,scrape_baidu_links=i.baidu_links,links=[CloudShareLink(url=j,title=i.movie.title_season)for j in i.movie.share_links],movie=i.movie) for i in scrape_result])

        filter_result=await title_and_episode_filter_flow(link_parse_results,params.skip_not_latest_episode)


        result=await save_to_cloud(filter_result)
        await save_to_database(result)
        progress_callback(100)
        return result




class P2(BaseModel):
    key:str=Field(default='鬼吹灯',description='关键词')
@registry.register(name="从豆瓣搜索", params_model=P2)
async def search_douban(params:P2,progress_callback, log_callback):

    r=await search_from_douban(params.key)
    progress_callback(100)
    return r




class P3(BaseModel):
    douban_infos:List[str]=Field(default='douban_id-movie_type',description='movietype=TV Movie')
    is_sync_cloud:bool=Field(default=False,description='是否同时抓取网盘分享链接同步到云盘')
    scrape_count: int = Field(default=3, description='每个影视爬取的网盘分享链接个数')
    skip_not_latest_episode: bool = Field(default=True, description='只爬取含有最新剧集的分享链接')
@registry.register(name="根据douban_id和movie_type保存影视元数据", params_model=P3)
async def get_by_douban_ids(params:P3,progress_callback, log_callback):
    douban_infos=params.douban_infos
    d_tuples=[]
    for douban_info in douban_infos:
        s_=douban_info.split('-')

        d_tuples.append((s_[0],MovieType(s_[1])))
    r=await registry_movie_data_sources(d_tuples)
    progress_callback(30)
    movies = await combin_to_movies(r)
    progress_callback(50)
    await save_to_database(movies)
    progress_callback(60)
    logger.info(f'已将该影视元数据入库{movies}')
    if not params.is_sync_cloud:
        progress_callback(100)
        return [
            movie.title_season for movie in movies
        ]
    else:
        logger.info(f'开始同步{[i.title_season for i in movies]}')
        progress_callback(20)
        to_save_movies = [i for i in movies if i.is_tmdb_infos_avaliable()]
        not_save_movies = [i for i in movies if not i.is_tmdb_infos_avaliable()]
        logger.warning(f'这些movie由于tmdb_info为空无法同步：{not_save_movies}')
        progress_callback(70)
        scrape_result = await link_scraping(to_save_movies, count=params.scrape_count)
        progress_callback(80)

        link_parse_results = await link_parse([PrepareParseLinks(scrape_quark_links=i.quark_links,scrape_baidu_links=i.baidu_links, links=[
            CloudShareLink(url=j, title=i.movie.title_season) for j in i.movie.share_links], movie=i.movie) for i in
                                               scrape_result])

        filter_result = await title_and_episode_filter_flow(link_parse_results, params.skip_not_latest_episode)

        result = await save_to_cloud(filter_result)
        await save_to_database(result)
        progress_callback(100)
        return result




class P4(BaseModel):
    ...
@registry.register(name="获取今日新的影视，从人人视频抓取", params_model=P4)
async def get_today_new_movie_metadata(params:P4,progress_callback, log_callback):
    new_movies= await renren_new_movie_provider_service.get_today_new_movie_metadata()
    progress_callback(50)
    movies= await save_new_movies_metadata_to_database(new_movies)
    progress_callback(100)
    return [[m.title_season for m in movies]]


class P6(BaseModel):
    air_days:int=Field(default=7,description='只推送上映时间多少天内的movie')
    is_delete_old_message:bool=Field(default=True,description='是否删除旧消息')

@registry.register(name='将所有网盘已更新到最新进度的movie推送到平台',params_model=P6)
async def p6(params:P6,progress_callback, log_callback):
    air_date1=datetime.now(pytz.timezone("Asia/Shanghai")).date()
    air_date2=(air_date1-timedelta(days=params.air_days))
    movies=await movie_repository.find(
        filters={
            'pubdate__gte':air_date2,
            'pubdate__lte':air_date1,
        }
    )
    print([i.title_season for i in movies])

    target_movies=[]
    for movie in movies:
        if movie.is_clouds_synced_latest():
            target_movies.append(movie)
    logger.info(f'将{[i.title_season for i in target_movies]}发布至平台')
    result_movies=  await share_link_publish_service.publish(target_movies,is_delete_old=params.is_delete_old_message)
    return {
        i.title_season:i.publish_to_platform_infos
        for i in result_movies
    }

class P7(BaseModel):
    douban_ids:List[str]=Field(default_factory=list,description='douban id')
    is_delete_old_message:bool=Field(default=True,description='是否删除旧消息')

@registry.register(name='将指定的movie推送到平台',params_model=P7)
async def p7(params:P7,progress_callback, log_callback):
    print(params)
    f_movies = await Movie.find(In(Movie.douban_id, params.douban_ids)).to_list()


    target_movies=[]
    for movie in f_movies:
        if len([i for i in movie.cloud_infos if i.share_link]):
            target_movies.append(movie)
    logger.info(f'将存在share_link的{target_movies}发布至平台')
    await share_link_publish_service.publish(target_movies,is_delete_old=params.is_delete_old_message)

class P8(BaseModel):
    air_days:int=Field(default=30,description='只检测上映时间多少天内的movie')
    douban_ids:List[str]=Field(default=[],description='如果不为空则忽略air_days')
    is_handle:bool=Field(default=True,description='处理风险文件(删除,混肴title_season,只保存torrent zip)')
    is_detect:bool=Field(default=True,description='检测风险链接')
@registry.register(name='检测与处理被和谐的分享链接',params_model=P8)
async def f8(params:P8,progress_callback, log_callback):
    async with lock1:
        if not params.douban_ids:
            air_date1 = datetime.now(pytz.timezone("Asia/Shanghai")).date()
            air_date2 = (air_date1 - timedelta(days=params.air_days))
            movies = await movie_repository.find(
                filters={
                    'pubdate__gte': air_date2,
                    'pubdate__lte': air_date1,
                }
            )
        else:

            movies=await Movie.find(In(Movie.douban_id, params.douban_ids)).to_list()
        r=None
        if params.is_detect:
            r = await    detect_risk_share(movies)

            r_movies=[i.movie for i in r]
            await save_to_database(r_movies)
            movies=r_movies
        h_r=None
        if params.is_handle:
            h_r=  await handle_risk_file_service.handle(movies)

            await save_to_database(movies)

        return {
            'detect_result':{
                i.movie.title_season: [
                    j.share_link for j in i.risk_cloud_infos
                ]

                for i in (r or [])

            },
            'handle_result':{
                i.movie.title_season: [
                    j.share_link for j in i.handle_cloud_infos
                ]

                for i in (h_r or [])

            }

        }

class RecreateDirDTO(BaseModel):
    air_days: int = Field(default=30, description='只检测上映时间多少天内的movie')
    douban_ids: List[str] = Field(default=[], description='如果不为空则忽略air_days')
    pan_names:List[str]=Field(default=[],description='被重建的网盘')
@registry.register(name='重建网盘影视目录',params_model=RecreateDirDTO)
async def recreate_dir_flow(params:RecreateDirDTO,progress_callback, log_callback):
    async with lock1:
        if not params.douban_ids:
            air_date1 = datetime.now(pytz.timezone("Asia/Shanghai")).date()
            air_date2 = (air_date1 - timedelta(days=params.air_days))
            movies = await movie_repository.find(
                filters={
                    'pubdate__gte': air_date2,
                    'pubdate__lte': air_date1,
                }
            )
        else:

            movies=await Movie.find(In(Movie.douban_id, params.douban_ids)).to_list()
        for movie in movies:
            await recreate_dir(movie,[i for i in movie.cloud_infos if i.pancloud_name in params.pan_names])

        await save_to_database(movies)






async def main():
    await init_db()
    setup_logging()
    tmdbsimple.API_KEY = settings.TMDB_API_KEY

    # await task_manager.task_manager.create_task('豆瓣热门影视采集',HotCollectParams(categories=[MovieCategory.CHINA],count=10).model_dump(),registry.get('豆瓣热门影视采集').fn)
    # await task_manager.task_manager.create_task('豆瓣热门影视采集', HotCollectParams(categories=[MovieCategory.CHINA],
    #                                                                                  count=10).model_dump(),
    #                                             registry.get('豆瓣热门影视采集').fn)
    r= await recreate_dir_flow(RecreateDirDTO(),lambda i:...,lambda i:...)
    # r=  await f8(P8(douban_ids=['36645835']),lambda i:...,lambda i:...)
    print(r)
    await asyncio.sleep(60)
if __name__ == '__main__':
    asyncio.run(main())
