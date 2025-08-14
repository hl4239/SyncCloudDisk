from typing import Optional, List

import pydantic
from pydantic import Field, BaseModel

from app.domain.models.resource import TvCategory

class ThemMovieCrawlerInfo(BaseModel):
    total_episodes:Optional[str]=Field(default=None,description='从themmovie网站爬到的原始剧集信息')
    title:Optional[str]=Field(default=None)
    episodes_url:Optional[str]=Field(default=None)

class DouBanCrawlerInfo(pydantic.BaseModel):
    title: Optional[str] = Field(default=None)
    subtitle: Optional[str] = None
    description: Optional[str] = Field(default=None)
    tv_category: Optional[TvCategory] = Field(default=TvCategory.OTHER)
    total_episodes: Optional[str] = None
    image_path: Optional[str] = None
    tags: List[str] = Field(default=None)






