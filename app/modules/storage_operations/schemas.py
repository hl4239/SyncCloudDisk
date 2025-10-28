from typing import Optional, List

from pydantic import BaseModel, Field, computed_field

from app.database.models import MovieCloudInfo, Movie
from app.modules.data_standard.schemas import StandardizedResult
from app.modules.link_parse.schemas import FileType
from app.utils.lazy_load import Lazy, lazy


class CloudFile(BaseModel):
    """
    【核心模型】: 使用复合模式，统一表示文件和文件夹。
    """
    # --- 通用字段 ---
    type: FileType = Field(None, description="条目类型：文件或文件夹")
    name: str = Field(None, description="文件名或文件夹名")
    standardized:Lazy[StandardizedResult] =Field(default_factory=lambda: lazy(None),description='标准化后的')
    id: Optional[str] = Field(None, description="在网盘系统中的唯一ID")
    parent_id: Optional[str] = Field(None, )
    path:Optional[str]=Field(None)
    # --- 文件夹专属字段 ---
    children: Optional[Lazy[List['CloudFile']]] = Field(default_factory=lambda: lazy(None), description="子条目列表 (仅文件夹拥有)")

    # --- 文件专属字段 ---
    size_bytes: Optional[int] = Field(None, description="文件大小（字节）(仅文件拥有)")

    @computed_field
    @property
    def is_folder(self) -> bool:
        return self.type==FileType.FOLDER

class HandleRiskFileResult(BaseModel):
    movie:Movie
    handle_cloud_infos:List[MovieCloudInfo]
