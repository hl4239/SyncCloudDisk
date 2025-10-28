import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from app.database.models import PanCloud, CloudType
from app.modules.link_parse.schemas import ShareFile,FileType, QuarkLinkParse
from app.modules.storage_operations.interfaces.cloud_disk_operator_interface import ICloudDiskOperator
from app.modules.storage_operations.schemas import CloudFile
from app.utils.cache import async_ttl_cache
from app.modules.link_parse.schemas import BaiduLinkParse
from app.modules.storage_operations.clients.baidu_cloud_client import get_baidu_pcs_client
from app.utils.lazy_load import lazy

logger=logging.getLogger(__name__)
class BaiduCloudOperator(ICloudDiskOperator):




    async def delete_file(self, share_files: List[CloudFile]):
        client = await self._get_client()
        try:
            r = await client.delete([i.path for i in share_files])
            return r
        except Exception as e:
            logger.error(e, exc_info=True)

            return False

    @async_ttl_cache
    async def  _get_pan_cloud(self):
        return await PanCloud.find_one(PanCloud.name == self.pancloud_name)

    async def _get_client(self):
        r=await get_baidu_pcs_client(await self._get_pan_cloud())
        if not r:
            raise Exception(f"PanCloud {self.pancloud_name}连接失败")
        return r

    async def rename(self, share_file: ShareFile, new_name: str):
        client = await self._get_client()
        return await client.rename(share_file.path, new_name)
    @staticmethod
    def get_file_type(isdir):
        if isdir==0:
            return FileType.FILE
        else :
            return FileType.FOLDER

    async def ls_dir_(self,pdir_file: Optional[CloudFile] = None) -> Optional[List[CloudFile]]:
        client =await self._get_client()

        resp_json = await client.list(pdir_file.path)
        result = []

        for i in resp_json:
            cloud_file = CloudFile(
                id=str(i["fs_id"]),
                name=i["server_filename"],
                path=i["path"],
                type=self.get_file_type(i["isdir"]) ,
                children=lazy(None)
            )
            result.append(cloud_file)
        return result

    async def get_dir_(self, path: Path) -> Optional[CloudFile]:
        if path==Path('/'):
            return CloudFile(
                id='0',
                name='根',
                type=FileType.FOLDER,
                path='/',
                children=lazy(None),

            )


        client =await self._get_client()
        try:

            resp_json = await client.list(path.parent.as_posix())
        except Exception as e:
            logger.debug(f'从网盘获取目录信息失败:error:{e}')
            return None
        path_str=path.as_posix()
        dir_json=None
        for i in resp_json:
            if i['path'] == path_str:
                dir_json=i
        print(dir_json)
        result = []
        try:
            i=dir_json
            cloud_file = CloudFile(
                id=str(i["fs_id"]),
                name=i["server_filename"],
                type=self.get_file_type(i["isdir"]),
                path=i["path"],
                children=lazy(None)
            )
            return cloud_file
        except Exception as e:
            logger.warning(f'未get到{path}:{e}')
            return None



    async def mkdir(self, path: Path) -> Optional[CloudFile]:
        cloud_api = await self._get_client()
        path_str=path.as_posix()
        logger.debug(f'正在创建目录,path={path_str},name={self.pancloud_name}')

        try:
            await cloud_api.mkdir(path_str)
            await asyncio.sleep(1)
            r= await self.get_dir(path)
            if r :
                logger.debug(f'目录创建成功,path={path_str},name={self.pancloud_name}')
                return r
            else :
                logger.warning(f'已请求目录创建，但最终未查询到目录对象,path={path_str},name={self.pancloud_name}')
                return None

        except Exception as e:

            logger.error(f'目录创建失败,path={path_str},name={self.pancloud_name},error={e}')
            return None

    async def save_file_(self, share_files: List[ShareFile], parse: BaiduLinkParse, path: Path=None,pdir_file:CloudFile=None)->bool:
        if not share_files:
            return True
        if path:
            if pdir_file:=await self.ensure_get_dir(path):
                client=await self._get_client()
                fids=[int(f.id) for f in share_files]
                return await client.save_from_share(remotedir=path.as_posix(),fs_ids=fids,uk=int(parse.uk),share_id=int(parse.share_id),sekey=parse.sekey,shared_url=parse.link.url)
            return False
        if pdir_file:
            client=await self._get_client()
            fids=[int(f.id) for f in share_files]
            return await client.save_from_share(remotedir=pdir_file.path,fs_ids=fids,uk=int(parse.uk),share_id=int(parse.share_id),sekey=parse.sekey,shared_url=parse.link.url)

        return False



    async def create_share_link(self,path:Optional[Path]=None,files: Optional[List[CloudFile]]=None,password:str='8u62'):
        if path:
            child_files=[await self.get_dir(path)]
        else:
            child_files=files
        if not child_files:
            logger.error(f'❌创建分享链接失败，child_files:{child_files}')
        f_paths=[i.path for i in child_files]
        client=await self._get_client()
        r= await client.share(remotepaths=f_paths,password=password)
        if not r:
            logger.error(f'❌创建分享链接失败:{r}')
            return None

        share_link_with_pwd=f'{r['link']}?pwd={password}'
        logger.info(f'✅创建分享链接：{share_link_with_pwd}')

        return share_link_with_pwd


async def main():
    from app.database.database import init_db
    from app.core.logging_config import setup_logging

    await init_db()
    setup_logging()
    quark=BaiduCloudOperator("4295baidu")
    await quark.ls_dir(path=Path('/资源分享'))

    ...
if __name__ == '__main__':
    asyncio.run(main())

