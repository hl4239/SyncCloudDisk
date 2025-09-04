from pydantic import BaseModel, Field, HttpUrl, validator, field_validator
from typing import Optional, List, Union, AsyncIterator
from datetime import datetime, timedelta
from enum import Enum

from pygments.lexer import default

from app.database.models import Movie, CloudType
from app.utils.lazy_load import Lazy



class ResourceLink(BaseModel):
    """
    用于在链接爬虫模块内部表示一个被抓取到的网盘资源链接。
    这是一个非持久化模型 (DTO - Data Transfer Object)。
    """

    # 核心信息
    url: HttpUrl = Field(..., description="资源的分享链接")
    title: str = Field(..., description="从分享页面或帖子中提取的原始标题")

    # 元数据
    link_type: CloudType = Field(default=None, description="网盘类型")
    share_password: Optional[str] = Field(None, description="分享密码（如果有）")

    # 状态与时间戳
    # 【核心变化】: 从 @validator 迁移到 @field_validator
    @field_validator('link_type', mode='before')
    @classmethod
    def determine_link_type(cls, v, values):
        """在验证前，根据 URL 自动判断链接类型"""
        url_str = str(values.get('url', ''))
        if "pan.baidu.com" in url_str:
            return CloudType.BAIDU
        if "pan.quark.cn" in url_str:
            return CloudType.QUARK
        return None
class LinkScrapeResult(BaseModel):
    quark_links: Optional[List[Lazy[ResourceLink]]] = Field(default=None,description='')
    movie_info:Movie