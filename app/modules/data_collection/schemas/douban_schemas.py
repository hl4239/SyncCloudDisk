from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

from app.database.models import MovieType, MovieCategory
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
    def get_movie_type(self):
        douban_type=self.type
        if douban_type == 'tv':
            return MovieType.TV
        elif douban_type == 'movie':
            return MovieType.MOVIE
        else:
            return MovieType.OTHER

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
    id: Lazy[str]=Field(default_factory=lambda: lazy(None))
    title: Lazy[str]=Field(default_factory=lambda: lazy(None))
    original_title:Lazy[str]=Field(default_factory=lambda: lazy(None))
    subtype: Lazy[str] = Field(default_factory=lambda: lazy(None),description='tv movie')
    pic:Lazy[Pic] =Field(default_factory=lambda: lazy(None))
    year: Lazy[str]=Field(default_factory=lambda: lazy(None))
    episodes_count: Lazy[int]=Field(default_factory=lambda: lazy(None))
    card_subtitle: Lazy[str]=Field(default_factory=lambda: lazy(None))
    intro: Lazy[str]=Field(default_factory=lambda: lazy(None))
    countries: Lazy[List[str]]=Field(default_factory=lambda: lazy(None))
    pubdate:  Lazy[List[str]]=Field(default_factory=lambda: lazy(None))


    async def get_movie_type(self):
        douban_type=await self.subtype
        if douban_type == 'tv':
            return MovieType.TV
        elif douban_type == 'movie':
            return MovieType.MOVIE
        else:
            return MovieType.OTHER

    async def get_category(self):
        countries = await self.countries
        first_country = countries[0]
        if any(kw == first_country for kw in ['中国', '中国大陆', '大陆', '中国香港']):
            return MovieCategory.CHINA
        elif any(kw == first_country for kw in ['美国',
                                                "英国", "法国", "德国", "意大利", "西班牙", "葡萄牙",
                                                "荷兰", "比利时", "卢森堡", "瑞士", "奥地利", "爱尔兰",
                                                "挪威", "瑞典", "芬兰", "丹麦", "冰岛",
                                                "希腊", "塞浦路斯", "马耳他",
                                                "波兰", "捷克", "斯洛伐克", "匈牙利",
                                                "罗马尼亚", "保加利亚", "克罗地亚", "斯洛文尼亚",
                                                "塞尔维亚", "黑山", "北马其顿", "阿尔巴尼亚", "科索沃",
                                                "爱沙尼亚", "拉脱维亚", "立陶宛",
                                                "白俄罗斯", "乌克兰", "摩尔多瓦"
                                                ]
                 ):
            return MovieCategory.EUROPE
        elif any(kw == first_country for kw in ['韩国']):
            return MovieCategory.KOREA
        elif any(kw == first_country for kw in ['日本']):
            return MovieCategory.JAPAN
        else:
            return MovieCategory.OTHER

    async def get_total_episodes(self):
        return f'{await self .episodes_count}集全'

    async def get_pubdate(self):
        date_str = (await self.pubdate)[0]
        # 去掉括号和里面的内容
        clean_date = date_str.split("(")[0]
        # 转换为 datetime 对象
        dt = datetime.strptime(clean_date, "%Y-%m-%d").date()
        return dt




class DoubanSearchItem(BaseModel):
    douban_id: str
    title:str
    movie_type:MovieType
    pic:str
    year:str
