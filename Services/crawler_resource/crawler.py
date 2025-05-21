from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

class ResourceType(str, Enum):
    MAGNET = "magnet"
    TORRENT = "torrent"
    QUARK_VIDEO = "quark_video"
@dataclass
class Resource:
    url: Optional[str]            # 磁力链接或种子URL
    title: str          # 资源标题
    type: ResourceType  # 类型（枚举）
    format_name:Optional[str]= field(default=None)
@dataclass
class QuarkFile:
    fid:str
    share_fid_token:str
    file_name:str
    format_name:Optional[str]= field(default=None)
@dataclass
class ResourceQuark:
    title:Optional[str]
    url: Optional[str]
    file_list:list[QuarkFile]





@dataclass
class SearchResult:
    keyword:str
    result: Optional[list[any]] = None  # 可能为None