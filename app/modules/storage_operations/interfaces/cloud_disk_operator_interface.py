from abc import abstractmethod
from pathlib import Path
from typing import List, Optional

from app.modules.data_standard.schemas import StandardizedResult
from app.modules.data_standard.services.regex_standardizer import regex_standardizer
from app.modules.link_parse.schemas import ShareFile, LinkParse
from app.modules.storage_operations.schemas import CloudFile
from app.utils.lazy_load import lazy


class ICloudDiskOperator:


    @abstractmethod
    async def ls_dir_(self,pdir_file:Optional[CloudFile]=None)->Optional[List[CloudFile]]:
        """
        不递归

        :param pdir_file:

        :return:
        """
        ...

    async def ls_dir(self,path:Optional[Path]=None,pdir_file:Optional[CloudFile]=None)->Optional[List[CloudFile]]:
        """
        注册递归逻辑，增加标准化
        选择不为None的参数，优先path，
        都为none则返回none

        :param pdir_file:
        :param path:
        :return:
        """
        if not path and not pdir_file:
            return None
        if path :
            pdir_file=await self.get_dir(path)
        if not pdir_file.is_folder:
            raise Exception('无法ls非文件夹')
        pdir_file.standardized=lazy(lambda i=pdir_file.name:regex_standardizer.get_standardized_result(target_original= i.name,items= [StandardizedResult(original_name=i,is_folder=True)]))


        pdir_file.children=lazy(lambda :self.ls_dir_(pdir_file))

        standards=[StandardizedResult(original_name=i.name,is_folder=i.is_folder) for i in await pdir_file.children]

        for child in await  pdir_file.children:
            child.standardized=lazy(lambda i=child :regex_standardizer.get_standardized_result(target_original= i.name,items= standards))
            if child.is_folder:
                child.children = lazy(lambda: self.ls_dir(child))
        return await pdir_file.children


    @abstractmethod
    async def get_dir_(self, path: Path) -> Optional[CloudFile]:
        ...

    async def get_dir(self,path:Path)->Optional[CloudFile]:
        """只返回父目录信息，并标准化，不遍历子节点"""
        file= await self.get_dir_(path)
        if file:
            file.standardized=lazy(lambda :regex_standardizer.get_standardized_result(target_original=file.name,items=[StandardizedResult(original_name=file.name,is_folder=True)]))
        return file


    @abstractmethod
    async def mkdir(self,path:Path)-> Optional[CloudFile]:
        ...

    async def ensure_get_dir(self,path:Path)-> Optional[CloudFile]:
        if val:= await self.get_dir(path):
            return val
        return await self.mkdir(path)
    @abstractmethod
    async def save_file(self,share_files:List[ShareFile],parse:LinkParse,path:Path):
        ...

    @abstractmethod
    async def rename(self,share_file:ShareFile,new_name:str):
        ...
    @abstractmethod
    async def create_share_link(self, path: Optional[Path] = None, files: Optional[List[CloudFile]] = None,password: str = None):
        ...