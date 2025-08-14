import random
from abc import ABC, abstractmethod
from typing import Optional

import aiohttp
from numpy.f2py.auxfuncs import throw_error

from app.infrastructure.config import CloudAPIConfig


class CloudAPIABC(ABC):

    def __init__(self,config:CloudAPIConfig):
        self.name = config.name
        self.cookies=config.cookies
        self.session=None
    @abstractmethod
    def init_session(self):
        pass


    async def request(self, method: str, url: str, *,
                       params=None, data=None, json=None, headers=None):


        result=   await  self.session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json,
            headers=headers,
        )
        return result
    @abstractmethod
    async def get_fids(self, file_paths: list[str]):
        pass

    @abstractmethod
    async def ls_dir(self, pdir_fid, **kwargs):
        pass

    @abstractmethod
    async def mkdir(self, dir_path: str) -> bool:
        ...

    @abstractmethod
    async def save_file(self, fid_list, fid_token_list, to_pdir_fid: str, pwd_id, stoken):
        ...
    @abstractmethod
    async def create_share_link(self, fid_list: [], title: str, password: Optional[str] = None, expired_type: int = 1,
                                url_type: int = 1) -> Optional[str]:
        ...

    @abstractmethod
    async def connect(self):
        pass

    async def close(self):
        await self.session.close()
