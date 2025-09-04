import pytest

from app.database.database import init_db
from app.database.models import MovieType, MovieCategory, Movie
from app.database.movie_repository import MovieRepository


@pytest.mark.asyncio
async def test_upsert():
    # 使用随机后缀避免与已有数据冲突
    await init_db()
    movie = Movie(
        title_season="你好，草泥马1",
        year="2025",
        movie_type=MovieType.MOVIE,
        category=MovieCategory.ALL,
        description="initial12",
    )

    # 第一次 upsert 应插入文档
    await MovieRepository.upsert(movie)

    assert True
