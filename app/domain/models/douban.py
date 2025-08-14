from typing import List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

from app.domain.models.resource import TvCategory






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

