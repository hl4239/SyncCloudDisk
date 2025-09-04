import re
from typing import Union, Tuple, Optional, List, override

from pydantic import BaseModel

from app.database.models import Movie, MovieType, MovieCategory, TVCategory
from app.modules.data_collection.interfaces.mapper_interface import IMapper
from app.modules.data_collection.schemas.douban_schemas import DoubanTVResponse, DoubanTVItem
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.utils.lazy_load import lazy


class DoubanMapperService(IMapper):


    def _get_movie_type(self,douban_item:DoubanTVItem)->MovieType:
        douban_type=douban_item.type
        if douban_type=='tv':
            return MovieType.TV
        elif douban_type=='movie':
            return MovieType.MOVIE
        else:return MovieType.OTHER

    def _get_movie_category(self,douban_item:DoubanTVItem)->Union[MovieCategory, TVCategory]:
        movie_type=self._get_movie_type(douban_item)
        card_subtitle = douban_item.card_subtitle
        if movie_type==MovieType.TV:

            if any(kw in card_subtitle for kw in ['中国']):
                return TVCategory.CHINA
            elif any(kw in card_subtitle for kw in ['英国','美国']):
                return TVCategory.EUROPE
            elif any(kw in card_subtitle for kw in ['韩国']):
                return TVCategory.KOREA
            elif any(kw in card_subtitle for kw in ['日本']):
                return TVCategory.JAPAN
            else:return TVCategory.OTHER
        elif movie_type==MovieType.MOVIE:
            return MovieCategory.ALL
        else:
            return TVCategory.OTHER




    def extract_title_season(self,raw_title: str, patterns: List[str]) -> Tuple[str, Optional[str]]:
        """
        通用正则解析框架
        :param raw_title: 原始标题
        :param patterns: 正则表达式列表，每个必须至少有1个捕获组(title)和可选的第2个捕获组(season)
        :return: (title, season) - season 匹配不到返回 None
        """
        s = raw_title.strip()

        for pattern in patterns:
            m = re.match(pattern, s, re.IGNORECASE)
            if m:
                # group(1) 是标题，group(2) 可选是季
                title = m.group(1).strip()
                season = m.group(2).strip() if m.lastindex and m.lastindex >= 2 else None
                return title, season

        # 如果所有正则都没匹配到，就返回原始字符串 + None
        return s, None


    def _get_movie_title_season(self,douban_item:DoubanTVItem)-> tuple[str, str | None]:
        regex_rules = [
            r"^(.*?)(\d+)$",  # 规则1: 最后一个空格 + 数字
            r"^(.*?) (第.+季)$",  # 规则3: 结尾是 "第X季"/S数字
        ]
        title_season=douban_item.title
        title,season=self.extract_title_season(title_season, regex_rules)
        print(title,season)
        return title,season

    def _get_movie_episodes(self,douban_item:DoubanTVItem)->tuple[Optional[str], Optional[str]]:
        """

        :param douban_item:
        :return: 当前更新的剧集，总剧集
        """
        episodes_info=douban_item.episodes_info
        if episodes_info==""or episodes_info is None:
            return None,None
        elif '更新至' in episodes_info:
            return episodes_info,None
        elif '全' in episodes_info:
            return episodes_info,episodes_info
        else:
            raise RuntimeError(f'未处理的未知值episodes_info:{episodes_info}')

    @override
    def map_to_movie(self, original: DoubanTVItem) -> Movie:
        year = original.year
        description = original.comment
        tv_type = self._get_movie_type(original)
        title_season = original.title
        tv_category = self._get_movie_category(original)
        current_episodes, total_episodes = self._get_movie_episodes(original)
        return Movie(title_season=title_season, year=year, description=description, movie_type=tv_type,category=tv_category, current_episodes=current_episodes, total_episodes=total_episodes)
    @override
    def map_to_movies(self,original:DoubanTVResponse)->list[Movie]:
        douban_items=original.subject_collection_items
        movies=[]
        for douban_item in douban_items:
            movies.append(self.map_to_movie(douban_item))
        return movies
    def map_to_movie_data_source(self, original: DoubanTVItem) -> MovieDataSourceResult:
        douban_id=original.id
        year = original.year
        description = original.comment
        tv_type = self._get_movie_type(original)
        title_season = original.title
        tv_category = self._get_movie_category(original)
        current_episodes, total_episodes = self._get_movie_episodes(original)
        movie_data_source=MovieDataSourceResult()
        movie_data_source.douban_id=lazy(douban_id)
        movie_data_source.year =lazy(year)
        movie_data_source.description = lazy(description)
        movie_data_source.movie_type = lazy(tv_type)
        movie_data_source.title_season = lazy(title_season)
        movie_data_source.tv_category = lazy(tv_category)
        movie_data_source.current_episodes = lazy(current_episodes)
        movie_data_source.total_episodes = lazy(total_episodes)
        return movie_data_source

    def map_to_movies_data_source(self, original: DoubanTVResponse) -> list[MovieDataSourceResult]:
        douban_items = original.subject_collection_items
        movies = []
        for douban_item in douban_items:
            movies.append(self.map_to_movie_data_source(douban_item))
        return movies