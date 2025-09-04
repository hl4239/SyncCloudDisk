from typing import Any, Optional
from beanie import PydanticObjectId
from beanie.odm.operators.update.general import Set

from app.database.models import Movie

class MovieRepository:
    @staticmethod
    async def create(movie: Movie, session: Optional[Any] = None) -> Movie:
        # 在 beanie 中可以传入 session 来参与事务
        return await movie.insert(session=session)
    @staticmethod
    async def find_by_douban_id(douban_id: str) -> Optional[Movie]:
        return await Movie.find_one(Movie.douban_id == douban_id)

    @staticmethod
    async def upsert(movie: Movie, session: Optional[Any] = None) -> Movie:
        """
        如果具有相同 unique_key 的电影已存在，则更新它，否则创建新电影。
        """
        # 在 upsert 中必须提供更新操作，比如 $set
        await Movie.find_one(Movie.unique_key == movie.unique_key).upsert(
            Set(movie.model_dump(exclude_unset=True)),  # 指定更新操作
            on_insert=movie,  # 指定插入操作
            session=session
        )
        return movie