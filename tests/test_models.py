import datetime
import json
from datetime import date

import pytest

from app.database.database import init_db_sync, init_db
from app.database.models import EpisodesInfo, Movie, MovieType, TMDBInfos, TVCategory
from app.database.movie_repository import  movie_repository


def test_episodes_info():
    e = EpisodesInfo(air_date=date.today(), episode_number=1)
    es=[e]
    s=f'es:{es}'
    print(s)
@pytest.mark.asyncio
async def test_movie():

    await init_db()
    movie=await movie_repository.find_by_douban_id('36744135')
    movie.douban_id='1234'
    movie.id=None
    movie.revision_id=None

    movie=Movie(douban_id='asd',title_season='zxcz',movie_type=MovieType.MOVIE)
    movie.episodes_info=[EpisodesInfo(air_date=date.today(), episode_number=1,air_time=datetime.time(12,0))]

    print(movie)

    await movie_repository.upsert([movie],ignore_none=True)
    # movie=await movie_repository.find_by_douban_id('36172040')
    # await movie_repository.upsert([movie])
    #
    # movie = Movie(
    #
    #
    #     douban_id='36172040',
    #     title='献鱼',
    #     title_season='献鱼',
    #     subtitle=None,
    #     description=(
    #         "被封在山中五百年的庚辰仙府师祖司马焦（陈飞宇 饰）与意外来到修仙界的廖停雁（王影璐 饰）"
    #         "相遇后，被其无欲无求的“咸鱼”本能降服，从此廖停雁开始引导司马焦步步向善，成为了改变他的人，"
    #         "过程中他们萌生情愫，在仙府、魔域和人间经历了一段跨越三世的爱恨纠葛，最终两人选择守护爱人，维护三界太平。\n"
    #         "该剧改编自扶华的小说《向师祖献上咸鱼》。"
    #     ),
    #     year='2025',
    #     category=TVCategory.CHINA,
    #     movie_type=MovieType.TV,
    #     season='第一季',
    #     total_episodes='33集全',
    #     cloud_infos=None,
    #     tmdb_infos=TMDBInfos(id=254476, season_number=1, not_ensure=False),
    #     have_newer_episodes=False,
    #     episodes_info=[
    #         EpisodesInfo(
    #             episode_number=ep_num,
    #             air_date=ep_date,
    #             air_time=None,
    #             tz_offset=8,
    #
    #
    #         )
    #         for ep_num, ep_date, weekday in [
    #             (1, date(2025, 8, 16), "星期六"),
    #             (2, date(2025, 8, 16), "星期六"),
    #             (3, date(2025, 8, 16), "星期六"),
    #             (4, date(2025, 8, 16), "星期六"),
    #             (5, date(2025, 8, 17), "星期日"),
    #             (6, date(2025, 8, 17), "星期日"),
    #             (7, date(2025, 8, 18), "星期一"),
    #             (8, date(2025, 8, 18), "星期一"),
    #             (9, date(2025, 8, 19), "星期二"),
    #             (10, date(2025, 8, 19), "星期二"),
    #             (11, date(2025, 8, 20), "星期三"),
    #             (12, date(2025, 8, 20), "星期三"),
    #             (13, date(2025, 8, 21), "星期四"),
    #             (14, date(2025, 8, 21), "星期四"),
    #             (15, date(2025, 8, 22), "星期五"),
    #             (16, date(2025, 8, 22), "星期五"),
    #             (17, date(2025, 8, 23), "星期六"),
    #             (18, date(2025, 8, 23), "星期六"),
    #             (19, date(2025, 8, 24), "星期日"),
    #             (20, date(2025, 8, 24), "星期日"),
    #             (21, date(2025, 8, 25), "星期一"),
    #             (22, date(2025, 8, 26), "星期二"),
    #             (23, date(2025, 8, 27), "星期三"),
    #             (24, date(2025, 8, 27), "星期三"),
    #             (25, date(2025, 8, 28), "星期四"),
    #             (26, date(2025, 8, 29), "星期五"),
    #             (27, date(2025, 8, 30), "星期六"),
    #             (28, date(2025, 8, 30), "星期六"),
    #             (29, date(2025, 8, 31), "星期日"),
    #             (30, date(2025, 9, 1), "星期一"),
    #             (31, date(2025, 9, 1), "星期一"),
    #             (32, date(2025, 9, 1), "星期一"),
    #             (33, date(2025, 9, 1), "星期一"),
    #         ]
    #     ]
    # )
    #
    #


