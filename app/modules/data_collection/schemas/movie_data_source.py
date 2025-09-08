from pydantic import BaseModel

from app.database.models import TVCategory, MovieCategory, MovieType, MovieStatus, TMDBInfos, Movie, MovieCloudInfo
from app.utils.lazy_load import Lazy, lazy


class MovieDataSourceResult(BaseModel):
    douban_id:Lazy[str]=lazy(None)
    title: Lazy[str]=lazy(None)
    title_season: Lazy[str]=lazy(None)
    subtitle: Lazy[str]=lazy(None)
    description: Lazy[str]=lazy(None)
    year: Lazy[str]=lazy(None)
    category: Lazy[MovieCategory|TVCategory]=lazy(None)
    movie_type: Lazy[MovieType]=lazy(None)
    season:Lazy[str]=lazy(None)
    total_episodes: Lazy[str]=lazy(None)
    current_episodes:Lazy[str]=lazy(None)
    status: Lazy[MovieStatus]=lazy(None)
    tmdb_infos:Lazy[TMDBInfos]=lazy(None)
    movie_info:Lazy[Movie]=lazy(None)
