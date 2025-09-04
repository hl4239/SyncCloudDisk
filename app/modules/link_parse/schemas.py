from pydantic import BaseModel, Field, field_validator, ValidationInfo, model_validator
from typing import List, Optional, Union, Callable, Any
from enum import Enum
from pathlib import Path

from app.database.models import Movie
from app.modules.link_scraping.schemes.link import LinkScrapeResult, ResourceLink
from app.utils.lazy_load import Lazy


# --- FileType 枚举保持不变 ---
class FileType(str, Enum):
    FILE = "file"
    FOLDER = "folder"


class ShareItem(BaseModel):
    """
    【核心模型】: 使用复合模式，统一表示文件和文件夹。
    """
    # --- 通用字段 ---
    item_type: FileType = Field(..., description="条目类型：文件或文件夹")
    name: str = Field(..., description="文件名或文件夹名")
    standardized_name:str=Field(...,description='标准化后的名')
    item_id: Optional[str] = Field(None, description="在网盘系统中的唯一ID")
    parent: Optional['ShareItem'] = Field(None, exclude=True, repr=False, description="父节点引用")

    # --- 文件夹专属字段 ---
    children: Optional[List['ShareItem']] = Field(None, description="子条目列表 (仅文件夹拥有)")

    # --- 文件专属字段 ---
    size_bytes: Optional[int] = Field(None, description="文件大小（字节）(仅文件拥有)")

    def __init__(self, **data: Any):
        """重写构造函数，自动为子节点设置 parent 引用"""
        super().__init__(**data)
        if self.children:
            for child in self.children:
                child.parent = self

    # --- Pydantic 验证器，确保数据一致性 ---
    @field_validator('children')
    @classmethod
    def check_children_for_folders(cls, v: Optional[List['ShareItem']], info: ValidationInfo) -> Optional[
        List['ShareItem']]:
        if info.data.get('item_type') == FileType.FILE and v is not None:
            raise ValueError("Files cannot have children.")
        return v

    @field_validator('size_bytes')
    @classmethod
    def check_size_for_files(cls, v: Optional[int], info: ValidationInfo) -> Optional[int]:
        if info.data.get('item_type') == FileType.FOLDER and v is not None:
            raise ValueError("Folders cannot have a size.")
        return v

    # --- 导航和操作方法 (统一接口) ---

    def is_folder(self) -> bool:
        """判断是否是文件夹"""
        return self.item_type == FileType.FOLDER

    def get_path(self) -> Path:
        """获取该条目的完整路径"""
        if self.parent:
            return self.parent.get_path() / self.name
        # 对于根节点，可以考虑是否返回一个特殊的根路径
        return Path(self.name)

    def find_by_path(self, path: Union[str, Path]) -> Optional['ShareItem']:
        """
        根据相对路径查找子条目。
        """
        if not self.is_folder():
            return None  # 只有文件夹才能查找子节点

        p = Path(path)
        parts = p.parts

        current_node = self
        for part in parts:
            if not current_node.is_folder() or not current_node.children:
                return None

            found = False
            for child in current_node.children:
                if child.name == part:
                    current_node = child
                    found = True
                    break
            if not found:
                return None

        return current_node

    def walk(self, on_file: Callable[['ShareItem'], None], on_folder: Callable[['ShareItem'], None]):
        """
        【核心功能】: 遍历自身及所有子节点，并执行回调。
        这是一个简化的、内置的访问者模式。
        """
        if self.is_folder():
            on_folder(self)
            if self.children:
                for child in self.children:
                    child.walk(on_file, on_folder)  # 递归调用
        else:  # 是文件
            on_file(self)


# --- 为了向后兼容或在其他地方使用，可以创建类型别名 ---
# ShareFile = ShareItem
# ShareFolder = ShareItem

# --- LinkInspectionResult 模型的定义需要相应调整 ---
class LinkParseItem(BaseModel):
    link:ResourceLink
    root:Lazy[ShareItem]


class LinkParseResult(BaseModel):
    quark_parses:List[LinkParseItem]



