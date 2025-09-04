import datetime
import pytest

from app.database import database
from app.database.models import Movie, MovieType, CloudType, MovieCloudInfo, MovieCategory, PanCloud, \
    SplitTitleSeasonRegular, OpenAISource


@pytest.mark.asyncio
async def test_movie_store_and_retrieve():
    # 初始化数据库（会注册模型并创建索引）
    db = await database.init_db()
    assert db is not None


    # 创建并保存
    movie = Movie( title_season="Test Movie3556", year='2025 ',movie_type=MovieType.MOVIE,category=MovieCategory.ALL,cloud_infos=[MovieCloudInfo()])
    await movie.insert()
    assert True



@pytest.mark.asyncio
async def test_movie_find():
    # 初始化数据库（会注册模型并创建索引）
    db = await database.init_db()
    assert db is not None




    # 查询并断言
    fetched =  Movie.find_all()
    print('找到：',await fetched.count())
    assert True

@pytest.mark.asyncio
async def test_pan_cloud_storage():
    # 初始化数据库（会注册模型并创建索引）
    db = await database.init_db()
    assert db is not None


    # 创建并保存
    cloud=PanCloud(cloud_type=CloudType.BAIDU,cookie='aasdas',phone_tail='123456')

    await cloud.insert()
    assert True


@pytest.mark.asyncio
async def test_split_title_season_regular():
    # 初始化数据库（会注册模型并创建索引）
    db = await database.init_db()
    assert db is not None

    # # 创建并保存
    # r = SplitTitleSeasonRegular(regular= r"^(.*?) (第.+季)$",description='结尾是 "第X季"')
    #
    # await r.insert()
    res=await SplitTitleSeasonRegular.find_all().to_list()
    print(res)
    assert True
@pytest.mark.asyncio
async def test_open_ai_storage():
    # 初始化数据库（会注册模型并创建索引）
    db = await database.init_db()
    assert db is not None

    # 创建并保存
    r = OpenAISource(name='copilot',key='',models=['gpt-5'],base_url='http://192.168.31.2:5005/v1')

    await r.insert()

    assert True



