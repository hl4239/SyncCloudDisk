import asyncio
import logging
import time
from abc import abstractmethod
from collections import Counter
from pathlib import Path
from typing import List, Optional

from app.modules.data_standard.schemas import StandardizedResult
from app.modules.data_standard.services.regex_standardizer import regex_standardizer
from app.modules.link_parse.schemas import ShareFile, LinkParse
from app.modules.storage_operations.schemas import CloudFile
from app.utils.lazy_load import lazy

logger=logging.getLogger(__name__)
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
    async def save_file_(self,share_files:List[ShareFile],parse:LinkParse,path:Path=None,pdir_file:CloudFile=None)->bool:
        ...

    async def save_file(
            self,
            share_files: List[ShareFile],
            parse: LinkParse,
            path: Path=None,
            pdir_file: CloudFile=None,
            ensure_shared_file_exist: bool = True,
            wait_timeout: float = 5.0,
            poll_interval: float = 1,
    ) -> bool:
        """
        保存文件并可选地等待目标目录实际出现这些共享文件。
        :param pdir_file:
        :param share_files: 期望出现在目标目录的 ShareFile 列表（只使用 .name）
        :param parse: 解析参数（传入给 self.save_file_）
        :param path: 目标路径
        :param ensure_shared_file_exist: 是否等待并确认共享文件存在
        :param wait_timeout: 等待超时时间（秒）。<=0 表示只检查一次，不轮询。
        :param poll_interval: 轮询间隔（秒），仅当 wait_timeout>0 时生效。
        :return: True 表示成功并且（如果要求）文件已确认存在；False 表示失败或超时
        """
        # 先尝试保存（你的 existing save_file_）
        r = await self.save_file_(share_files, parse, path,pdir_file)
        if not r:
            return False

        # 不需要确认文件存在，直接返回成功
        if not ensure_shared_file_exist:
            return True
        if not share_files:
            return True
        # 预期文件名计数（考虑重复）
        expected_names = Counter([f.name for f in share_files])
        if path:
            pdir_file = await self.get_dir(path)
        # 轮询直到超时


        deadline = time.monotonic() + float(wait_timeout)
        while True:

            ls_files = await self.ls_dir(pdir_file=pdir_file)
            current_names = Counter([f.name for f in ls_files])
            if current_names >= expected_names:
                return True

            not_existed = expected_names - current_names
            if time.monotonic() >= deadline:
                # 超时仍未满足
                logger.warning(f'转存任务api提示成功，但轮询查询了{wait_timeout}秒发现实际还有未完成的转存：{not_existed}')
                return True

            # 等待下一轮检查
            await asyncio.sleep(poll_interval)


    @abstractmethod
    async def rename(self,share_file:ShareFile,new_name:str):
        ...
    @abstractmethod
    async def create_share_link(self, path: Optional[Path] = None, files: Optional[List[CloudFile]] = None,password: str = None):
        ...


