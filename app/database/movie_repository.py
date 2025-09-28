import asyncio
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional, List
from zoneinfo import ZoneInfo

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
            update_data = movie.model_dump(exclude_unset=False)

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

    @staticmethod
    async def find_movies_with_episode_on(
            date_: Optional[date] = None, tz: str = "Asia/Shanghai"
    ) -> List[Movie]:
        """
        在 DB 层查找：episodes_info 中存在 air_date 属于指定 date_ 的所有 Movie。
        - 支持三种常见情况：
          1. episodes_info.air_date 存为 date 类型（或被序列化为 date-like）；
          2. episodes_info.air_date 存为 ISO 字符串 "YYYY-MM-DD"；
          3. episodes_info.air_date 存为 datetime（则匹配该日的时间区间）。
        - 参数:
            date_: 要查找的日期（如果为 None，则根据 tz 计算“今天”）
            tz: 时区（例如 "Asia/Shanghai"），只用于计算 day-start/day-end 的 UTC 边界
        - 返回: 匹配的 Movie 列表（Beanie Document 对象）
        """
        # 计算目标日期（默认为 tz 的今天）
        if date_ is None:
            date_ = datetime.now(ZoneInfo(tz)).date()

        # 1) 直接用 date 值匹配（有些驱动会把 date 转为 BSON date）
        cond_date = {"episodes_info": {"$elemMatch": {"air_date": date_}}}

        # 2) 有些项目把日期存成字符串 "YYYY-MM-DD"
        iso_str = date_.isoformat()
        cond_str = {"episodes_info": {"$elemMatch": {"air_date": iso_str}}}

        # 3) 或者把日期存成 datetime（例如存为 2025-09-20T00:00:00Z），我们构造当天的 UTC 范围做匹配
        #    先把本地日期的 00:00 -> 转为 UTC；然后 next day 00:00 -> 转为 UTC
        local_start = datetime.combine(date_, time(0, 0), tzinfo=ZoneInfo(tz))
        local_end = local_start + timedelta(days=1)
        utc_start = local_start.astimezone(timezone.utc)
        utc_end = local_end.astimezone(timezone.utc)
        cond_datetime_range = {
            "episodes_info": {
                "$elemMatch": {"air_date": {"$gte": utc_start, "$lt": utc_end}}
            }
        }

        # 合并为 $or：任一条件匹配即可
        query = {"$or": [cond_date, cond_str, cond_datetime_range]}

        # 使用 Beanie 的 find 查询并返回列表（数据库层面过滤）
        cursor = Movie.find(query)
        return await cursor.to_list()

    @staticmethod
    async def find_movies_with_episode_today(tz: str = "Asia/Shanghai") -> List[Movie]:
        """查找指定时区的“今天”有剧集的 movies（便捷方法）"""
        today = datetime.now(ZoneInfo(tz)).date()
        return await MovieRepository.find_movies_with_episode_on(today, tz)
    @staticmethod
    async def find_by_metadata_provider(
        provider: "MetaDataProviderEnum | str",
        title: Optional[str] = None,
        provider_id: Optional[str] = None,
        session: Optional[Any] = None
    ) -> Optional[Movie]:
        """
        根据 metadata_providers 查询 Movie。
        - provider: 必须，MetaDataProviderEnum 或对应的字符串表示
        - title: 可选，匹配 metadata_providers.title（精确匹配）
        - provider_id: 可选，匹配 metadata_providers.id（精确匹配）
        - 如果同时传 title 和 provider_id，优先使用 provider_id
        返回第一个匹配到的 Movie 或 None。
        """
        if provider_id is None and title is None:
            raise ValueError("必须提供 title 或 provider_id 中的至少一个参数")

        # 构造 $elemMatch 条件
        elem_match = {"provider": provider}
        if provider_id is not None:
            elem_match["id"] = provider_id
        else:
            elem_match["title"] = title

        query = {"metadata_providers": {"$elemMatch": elem_match}}

        # 如果需要用 session（事务）可以传入 session 参数
        # 使用 find_one 返回单个文档
        return await Movie.find_one(query, session=session)


movie_repository=MovieRepository()
async def main():
    await init_db()
    # movies = [
    #     Movie(douban_id="123", title="电影A", year="2021",title_season='12',movie_type=MovieType.MOVIE,),
    #     Movie(douban_id="456", title="电影B", year=None,title_season='as3',movie_type=MovieType.MOVIE,),
    # ]
    #
    # # 批量 upsert
    # saved_movies = await MovieRepository.upsert(movies, ignore_none=True)
    #
    # for m in saved_movies:
    #     print(m.douban_id, m.title)
    r= await movie_repository.find_movies_with_episode_today()
    [print (i.title_season) for i in r]
if __name__ == '__main__':
    asyncio.run(main())