from pydantic import BaseModel, Field, field_validator, ValidationInfo, model_validator, computed_field, ConfigDict
from typing import List, Optional, Union, Callable, Any
from enum import Enum
from pathlib import Path

from app.database.models import Movie, CloudType, CloudShareLink
from app.modules.data_standard.schemas import StandardizedResult

from app.utils.async_iterator import AsyncCachedIterator
from app.utils.lazy_load import Lazy, lazy


# --- FileType 枚举保持不变 ---
class FileType(str, Enum):
    FILE = "file"
    FOLDER = "folder"


class ShareFile(BaseModel):
    """
    【核心模型】: 使用复合模式，统一表示文件和文件夹。
    """
    # --- 通用字段 ---
    type: FileType = Field(None, description="条目类型：文件或文件夹")
    name: str = Field(None, description="文件名或文件夹名")
    standardized:Lazy[StandardizedResult] =Field(lazy(None),description='标准化后的')
    id: Optional[str] = Field(None, description="在网盘系统中的唯一ID")
    parent_id: Optional[str] = Field(None, )
    share_fid_token:Optional[str] = Field(None, )
    # --- 文件夹专属字段 ---
    children: Optional[Lazy[List['ShareFile']]] = Field(lazy(None), description="子条目列表 (仅文件夹拥有)")

    # --- 文件专属字段 ---
    size_bytes: Optional[int] = Field(None, description="文件大小（字节）(仅文件拥有)")

    @computed_field
    @property
    def is_folder(self) -> bool:
        return self.type==FileType.FOLDER

class PrepareParseLinks(BaseModel):
    scrape_quark_links: Optional[Lazy[AsyncCachedIterator[CloudShareLink]]]=Field(default=lazy(None),description='从网络抓取的')
    links:Optional[list[CloudShareLink]]=Field(default=[],description='现有的')
    movie:Optional[Movie]=Field(None,description='')

# --- LinkInspectionResult 模型的定义需要相应调整 ---
class LinkParse(BaseModel):
    link:CloudShareLink=Field(None)
    root:ShareFile=Field(None)
    @computed_field
    @property
    def type(self) -> CloudType:
        return self.link.type

class QuarkLinkParse(LinkParse):
    pwd_id:Optional[str]=Field(None)
    passcode:Optional[str]=Field(None)
    pdir_fid:Optional[str]=Field(None)
    stoken:Optional[str]=Field(None)

class LinkParseResult(BaseModel):
    quark_parses:Optional[AsyncCachedIterator[QuarkLinkParse]]
    movie:Optional[Movie]
    model_config = ConfigDict(arbitrary_types_allowed=True)



