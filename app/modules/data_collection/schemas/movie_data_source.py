from datetime import date

from pydantic import BaseModel, computed_field

from app.database.models import MovieCategory, MovieType, TMDBInfos, Movie, MovieCloudInfo, \
    EpisodesInfo
from app.modules.data_collection.schemas.douban_schemas import DoubanDetailLazyResponse, DoubanDetailResponse
from app.utils.lazy_load import Lazy, lazy


class MovieDataSourceResult(BaseModel):
    douban_id:Lazy[str]=lazy(None)
    original_title:Lazy[str]=lazy(None)
    title: Lazy[str]=lazy(None)
    title_season: Lazy[str]=lazy(None)
    subtitle: Lazy[str]=lazy(None)
    pic: Lazy[str]=lazy(None)
    description: Lazy[str]=lazy(None)
    year: Lazy[str]=lazy(None)
    category: Lazy[MovieCategory]=lazy(None)
    movie_type: Lazy[MovieType]=lazy(None)
    season:Lazy[str]=lazy(None)
    total_episodes: Lazy[str]=lazy(None)
    tmdb_infos:Lazy[TMDBInfos]=lazy(None)
    episodes_info:Lazy[list[EpisodesInfo]]=lazy(None)
    pubdate: Lazy[date]=lazy(None)
    movie_info:Lazy[Movie]=lazy(None)



