import asyncio
from typing import Any, Optional, List
from beanie import PydanticObjectId
from beanie.odm.operators.update.general import Set

from app.database.database import init_db
from app.database.models import Movie, MovieType


class MovieRepository:
    @staticmethod
    async def create(movie: Movie, session: Optional[Any] = None) -> Movie:
        # 在 beanie 中可以传入 session 来参与事务
        return await movie.insert(session=session)
    @staticmethod
    async def find_by_douban_id(douban_id: str) -> Optional[Movie]:
        return await Movie.find_one(Movie.douban_id == douban_id)

    @staticmethod
    async def upsert(
        movies: List["Movie"],
        session: Optional[Any] = None,
        ignore_none: bool = True
    ) -> List["Movie"]:
        """
        批量 upsert 电影记录：
        - 如果具有相同 douban_id 的电影已存在，则更新它
        - 否则创建新电影
        参数:
            movies: List[Movie]
            ignore_none:
                - True: 只更新不为 None 的字段
                - False: 更新所有字段
        返回:
            List[Movie]
        """
        results: List["Movie"] = []

        for movie in movies:
            # dump 出字典
            update_data = movie.model_dump(exclude_unset=True)

            # ✅ 按需过滤掉 None
            if ignore_none:
                update_data = {k: v for k, v in update_data.items() if v is not None}

            # 执行 upsert
            await Movie.find_one(Movie.douban_id == movie.douban_id).upsert(
                Set(update_data),
                on_insert=movie,
                session=session
            )
            results.append(movie)

        return results

movie_repository=MovieRepository()
async def main():
    await init_db()
    movies = [
        Movie(douban_id="123", title="电影A", year="2021",title_season='12',movie_type=MovieType.MOVIE,),
        Movie(douban_id="456", title="电影B", year=None,title_season='as3',movie_type=MovieType.MOVIE,),
    ]

    # 批量 upsert
    saved_movies = await MovieRepository.upsert(movies, ignore_none=True)

    for m in saved_movies:
        print(m.douban_id, m.title)
if __name__ == '__main__':
    asyncio.run(main())