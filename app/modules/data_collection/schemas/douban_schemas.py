from typing import List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

from app.database.models import MovieType
from app.utils.lazy_load import Lazy, lazy


class Pic(BaseModel):
    large:str
    normal:str

# 主模型
class DoubanTVItem(BaseModel):
    id: str
    title: str
    type: str
    comment: Optional[str]
    pic: Pic
    year: str
    episodes_info: str
    # 可选字段
    card_subtitle:str
    photos: List[HttpUrl] = []
    tags: List[str] = []

# 响应包装
class DoubanTVResponse(BaseModel):
    count: int
    start: int
    total: int
    subject_collection_items: List[DoubanTVItem]
    subject_collection: dict
class DoubanDetailResponse(BaseModel):
    id: str
    title: str
    original_title:str
    subtype:str =Field(description='tv movie')
    pic:Pic
    year: str
    episodes_count:int
    card_subtitle: str
    intro:str
    countries: List[str]
    pubdate:List[str]

class DoubanDetailLazyResponse(BaseModel):
    id: Lazy[str]=lazy(None)
    title: Lazy[str]=lazy(None)
    original_title:Lazy[str]=lazy(None)
    subtype: Lazy[str] = Field(default=lazy(None),description='tv movie')
    pic:Lazy[Pic] =lazy(None)
    year: Lazy[str]=lazy(None)
    episodes_count: Lazy[int]=lazy(None)
    card_subtitle: Lazy[str]=lazy(None)
    intro: Lazy[str]=lazy(None)
    countries: Lazy[List[str]]=lazy(None)
    pubdate:  Lazy[List[str]]=lazy(None)
class DoubanSearchItem(BaseModel):
    douban_id: str
    title:str
    movie_type:MovieType
    pic:str
    year:str
