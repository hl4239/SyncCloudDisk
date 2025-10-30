from datetime import date
from typing import List

from pydantic import BaseModel, Field

from app.database.models import MovieCategory, MovieType, TMDBInfos, Movie, \
    EpisodesInfo
from app.utils.lazy_load import Lazy, lazy


class MovieDataSourceResult(BaseModel):
    douban_id: Lazy[str] = Field(default_factory=lambda: lazy(None))
    original_title_season: Lazy[str] = Field(default_factory=lambda: lazy(None))
    original_title: Lazy[str] = Field(default_factory=lambda: lazy(None))
    title: Lazy[str] = Field(default_factory=lambda: lazy(None))
    title_season: Lazy[str] = Field(default_factory=lambda: lazy(None))
    subtitle: Lazy[str] = Field(default_factory=lambda: lazy(None))
    pic: Lazy[str] = Field(default_factory=lambda: lazy(None))
    description: Lazy[str] = Field(default_factory=lambda: lazy(None))
    year: Lazy[str] = Field(default_factory=lambda: lazy(None))
    category: Lazy[MovieCategory] = Field(default_factory=lambda: lazy(None))
    movie_type: Lazy[MovieType] = Field(default_factory=lambda: lazy(None))
    season: Lazy[str] = Field(default_factory=lambda: lazy(None))
    total_episodes: Lazy[str] = Field(default_factory=lambda: lazy(None))
    tmdb_infos: Lazy[TMDBInfos] = Field(default_factory=lambda: lazy(None))
    episodes_info: Lazy[list[EpisodesInfo]] = Field(default_factory=lambda: lazy(None))
    pubdate: Lazy[date] = Field(default_factory=lambda: lazy(None))

    actors:Lazy[List[str]]=Field(default_factory=lambda: lazy(None),description='演员、配音')
    aliases:Lazy[List[str]]=Field(default_factory=lambda: lazy(None),description='别名')
    genres:Lazy[List[str]]=Field(default_factory=lambda: lazy(None),description='影视风格')


    movie_info: Lazy[Movie] = Field(default_factory=lambda: lazy(None))





