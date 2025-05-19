from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

class ResourceType(str, Enum):
    MAGNET = "magnet"
    TORRENT = "torrent"

@dataclass
class Resource:
    url: Optional[str]            # 磁力链接或种子URL
    title: str          # 资源标题
    type: ResourceType  # 类型（枚举）
    format_name:Optional[str]= field(default=None)

@dataclass
class SearchResult:
    keyword:str
    result: Optional[list[Resource]] = None  # 可能为None