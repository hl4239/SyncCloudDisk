import datetime
import json
from datetime import date

import pytest
import pytz
from beanie import PydanticObjectId

from app.database.database import init_db_sync, init_db
from app.database.models import EpisodesInfo, Movie, MovieType, TMDBInfos, PanCloud, CloudType, \
    MovieCloudInfo, MovieCategory
from app.database.movie_repository import  movie_repository
from app.services.movie_service import movie_service


def test_episodes_info():
    e = EpisodesInfo(air_date=date.today(), episode_number=1)
    es=[e]
    s=f'es:{es}'
    print(s)
@pytest.mark.asyncio
async def test_movie():
    print(datetime.datetime(2025,9,29,0,1,2,tzinfo=pytz.utc))
    await init_db()
    # movie=await movie_repository.find_by_douban_id('36744135')
    # movie.douban_id='1234'
    # movie.id=None
    # movie.revision_id=None
    #
    # movie=Movie(douban_id='asd',title_season='zxcz',movie_type=MovieType.MOVIE)
    # movie.episodes_info=[EpisodesInfo(air_date=date.today(), episode_number=1,air_time=datetime.time(12,0))]
    #
    # print(movie)
    #
    # await movie_repository.upsert([movie],ignore_none=True)

    # p = await PanCloud.find_one()
    # print(p)
    # movie = Movie(
    #
    #
    #     douban_id='123',
    #     title='测试1231',
    #     title_season='测试1',
    #     subtitle=None,
    #     description=(
    #         "被封在山中五百年的庚辰仙府师祖司马焦（陈飞宇 饰）与意外来到修仙界的廖停雁（王影璐 饰）"
    #         "相遇后，被其无欲无求的“咸鱼”本能降服，从此廖停雁开始引导司马焦步步向善，成为了改变他的人，"
    #         "过程中他们萌生情愫，在仙府、魔域和人间经历了一段跨越三世的爱恨纠葛，最终两人选择守护爱人，维护三界太平。\n"
    #         "该剧改编自扶华的小说《向师祖献上咸鱼》。"
    #     ),
    #     year='2025',
    #     category=MovieCategory.CHINA,
    #     movie_type=MovieType.TV,
    #     season='第一季',
    #     total_episodes='33集全',
    #     tmdb_infos=TMDBInfos(id=254476, season_number=1, not_ensure=False),
    #     have_newer_episodes=False,
    #     episodes_info=[
    #         EpisodesInfo(
    #             episode_number=ep_num,
    #             air_date=ep_date,
    #             air_time=None,
    #
    #
    #         )
    #         for ep_num, ep_date, weekday in [
    #             (1, date(2025, 9, 20), "星期六"),
    #
    #         ]
    #     ]
    #     ,
    #     create_time=datetime.datetime.now(pytz.timezone("Asia/Shanghai")),
    #     update_time=datetime.datetime.now(pytz.timezone("Asia/Shanghai")),
    #     pubdate=datetime.datetime(2025,9,28,0,1,tzinfo=pytz.timezone("Asia/Shanghai")).date()
    #
    # )
    # print(movie)
    # await movie_repository.upsert([movie])

    # await  movie_repository.upsert([movie])
    # movie = await Movie.find_one(Movie.douban_id == movie.douban_id)
    # print( movie)
    # movie.create_time= movie.create_time.astimezone(pytz.timezone("Asia/Shanghai"))
    r=  await movie_repository.find( filters={

            "has_shareable_movies": True,
        },
        )

    print([i.title_season for i in r])
    r = await movie_repository.find_movies_with_episode_today()

    print([i.title_season for i in r])
@pytest.mark.asyncio
async def test_pan_cloud():
    await init_db()
    # pan_cloud=PanCloud(phone_tail='1234',cloud_type=CloudType.QUARK)
    # await pan_cloud.insert()
    r=doc = await PanCloud.get(PydanticObjectId("68cbfdcc40c03fabbfaf66cb"))
    print(r)

@pytest.mark.asyncio
async def test_movie1():
    await init_db()
    r= r=  await movie_repository.find( filters={

            "title_season__contains": '许我耀眼',
        },
        )
    print(r[0].get_latest_episode_info())