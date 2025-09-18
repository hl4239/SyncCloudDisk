import re
from datetime import date
from typing import List, Optional

import cn2an

from app.database.models import Movie, EpisodesInfo
from app.database.movie_repository import movie_repository, MovieRepository
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.interfaces.movie_services_interface import IMovieService


class MovieService(IMovieService):
    def __init__(self,movie_repo:MovieRepository):
        self.movie_repo=movie_repo

    @staticmethod
    def douban_season_to_tmdb_season(douban_season):
        """
           将 '第一季' / '第二季' / '第十季' 转换为 '第 1 季' / '第 2 季' / '第 10 季'
           """
        if not douban_season:
            return None
        if douban_season.startswith("第") and douban_season.endswith("季"):
            # 去掉"第"和"季"
            num_cn = douban_season[1:-1]
            try:
                num = cn2an.cn2an(num_cn, "normal")
                return f"第 {num} 季"
            except Exception:
                # 转换失败，返回None
                return None
        return douban_season

    @staticmethod
    def number_to_current_episodes(number:int,is_finale:False):
        if number and isinstance(number,int) :
            if not is_finale:
                return f'更新至{number}集'
            return f'{number}集全'
        return None
    @staticmethod
    def number_to_total_episodes(number:int):
        return MovieService.number_to_current_episodes(number,is_finale=True)
    @classmethod
    def is_finale(cls,episodes_info:List[EpisodesInfo])->bool:
        """
        返回true的情况：
            1.为none
            2.is_air_date_full and 所有air_date<today

        :param episodes_info:
        :return:
        """
        if episodes_info:
            if cls.is_air_date_full(episodes_info):
                last_episode = episodes_info[-1]
                if last_episode.air_date < date.today():
                    return True
        else:
            return True
        return False
    @staticmethod
    def is_air_date_full(episodes_info:List[EpisodesInfo]):
        """

        如果存在一个剧集的air_date为none则返回false
        :param episodes_info:
        :return:
        """
        if episodes_info:
            for episode in episodes_info:
                if not episode.air_date:
                    return False
        return True
    @staticmethod
    def is_air_time_full(episodes_info:List[EpisodesInfo]):
        """
        所有存在的air_date对应的air_time也存在返回true
        :param episodes_info:
        :return:
        """
        if episodes_info:
            for episode in episodes_info:
                if episode.air_date:
                    if not episode.air_time:
                        return False
        return True


    @classmethod
    def create_episodes_info(cls,total_episodes)->List[EpisodesInfo]:
        """
        支持total为str或者int
        :param total_episodes:
        :return:
        """
        if not total_episodes:
            return []
        if isinstance(total_episodes,str):
            total_episodes =cls.extract_episode_number(total_episodes)
        episodes_infos=[]
        for i in range(1,total_episodes+1):
            episodes_info=EpisodesInfo(episode_number=i,)
            episodes_infos.append(episodes_info)
        return episodes_infos


    @staticmethod
    def extract_episode_number(ep: str) -> Optional[int]:
        """
        从剧集字符串中提取剧集号。
        支持格式：
            - "更新至xx集"
            - "xx集全"
        如果匹配成功，返回整数；否则返回 None。
        """
        if isinstance(ep,int):
            return ep
        if not ep:
            return 0

        # 匹配 "更新至xx集"
        match_update = re.match(r"更新至(\d+)集", ep)
        if match_update:
            return int(match_update.group(1))

        # 匹配 "xx集全"
        match_all = re.match(r"(\d+)集全", ep)
        if match_all:
            return int(match_all.group(1))

        return None
    @classmethod
    def get_episodes_later(cls, *episodes: str) -> Optional[str]:
        """
        从多个剧集信息字符串中提取最新剧集对应的参数。
        返回对应的原始字符串；如果解析失败返回 None。
        """
        latest: tuple[int, str] | None = None

        for ep in episodes:
            number = cls.extract_episode_number(ep)
            if number is not None:
                if latest is None or number > latest[0]:
                    latest = (number, ep)

        return latest[1] if latest else None
    async  def combin_to_movies(self,movie_data_sources:List[MovieDataSourceResult])->List[Movie]:
        """
        将movie_data_source与数据库的movie进行合并成最新的一个movie
        :param movies:
        :return:
        """
        movies=[]
        for movie_data_source in movie_data_sources:
            movie=await self.movie_repo.find_by_douban_id(await movie_data_source.douban_id)
            if not movie:
                movie = Movie(
                    douban_id=await movie_data_source.douban_id,
                    title=await movie_data_source.title,
                    title_season=await movie_data_source.title_season,
                    subtitle=await movie_data_source.subtitle,
                    description=await movie_data_source.description,
                    year=await movie_data_source.year,
                    category=await movie_data_source.category,
                    movie_type=await movie_data_source.movie_type,
                    season=await movie_data_source.season,
                    total_episodes=await movie_data_source.total_episodes,
                    tmdb_infos=await movie_data_source.tmdb_infos,
                    have_newer_episodes=False,
                   episodes_info=await movie_data_source.episodes_info
                )
            else:
                if not movie.title:
                    movie.title = await movie_data_source.title
                if not movie.season :
                    movie.season = await movie_data_source.season
                if not movie.total_episodes :
                    movie.total_episodes = await movie_data_source.total_episodes

                movie.episodes_info=await movie_data_source.episodes_info
                if movie.tmdb_infos is None:
                    movie.tmdb_infos = await movie_data_source.tmdb_infos
            movies.append(movie)
        print(movies)
        return movies

movie_service = MovieService(movie_repository)
if __name__ == '__main__':
    print(MovieService.douban_season_to_tmdb_season('第一季'))