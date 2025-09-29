import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from app.database.models import PanCloud
from app.modules.link_parse.schemas import ShareFile,FileType, QuarkLinkParse
from app.modules.storage_operations.clients.quark_cloud_client import get_quark_cloud_client
from app.modules.storage_operations.interfaces.cloud_disk_operator_interface import ICloudDiskOperator
from app.modules.storage_operations.schemas import CloudFile
from app.utils.cache import async_ttl_cache

logger=logging.getLogger(__name__)
class QuarkCloudOperator(ICloudDiskOperator):
    async def rename(self, share_file: ShareFile, new_name: str):
        client=await self._get_client()
        return await client.rename(share_file.id, new_name)

    def __init__(self,pancloud_name):
        self.pancloud_name = pancloud_name
    @async_ttl_cache
    async def  _get_pan_cloud(self):
        return await PanCloud.find_one(PanCloud.name == self.pancloud_name)

    async def _get_client(self):
        return await get_quark_cloud_client(await self._get_pan_cloud())
    @staticmethod
    def get_file_type(file_type):
        if file_type==0:
            return FileType.FOLDER
        else :
            return FileType.FILE

    async def ls_dir_(self,pdir_file: Optional[CloudFile] = None) -> Optional[List[CloudFile]]:
        client =await self._get_client()

        resp_json = await client.ls_dir(pdir_file.id)
        result = []

        for i in resp_json:
            cloud_file = CloudFile(
                id=i["fid"],
                name=i["file_name"],
                parent_id=i["pdir_fid"],
                type=self.get_file_type(i["file_type"]) ,
                children=None
            )
            result.append(cloud_file)
        return result

    async def get_dir_(self, path: Path) -> Optional[CloudFile]:
        client =await self._get_client()
        try:

            resp_json = await client.get_fids([path.as_posix()])
        except Exception as e:
            logger.debug(f'从网盘获取目录信息失败:error:{e}')
            return None
        logger.debug(f'从网盘获取目录信息:{resp_json}')
        result = []
        try:
            i=resp_json[0]
            cloud_file = CloudFile(
                id=i["fid"],
                name=i["file_name"],
                parent_id=i["pdir_fid"],
                type=self.get_file_type(i["file_type"]),
                children=None
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

    async def save_file_(self, share_files: List[ShareFile], parse: QuarkLinkParse, path: Path,pdir_file:CloudFile)->bool:
        if not share_files:
            return True
        if path:
            if pdir_file:=await self.ensure_get_dir(path):
                client=await self._get_client()
                fids=[f.id for f in share_files]
                fid_tokens=[f.share_fid_token for f in share_files]
                return await client.save_file(fid_list=fids, fid_token_list=fid_tokens, pwd_id=parse.pwd_id,
                                          stoken=parse.stoken, to_pdir_fid=pdir_file.id)
            return False
        if pdir_file:
            client=await self._get_client()
            fids=[f.id for f in share_files]
            fid_tokens=[f.share_fid_token for f in share_files]
            return await client.save_file(fid_list=fids, fid_token_list=fid_tokens, pwd_id=parse.pwd_id,
                                      stoken=parse.stoken, to_pdir_fid=pdir_file.id)

        return False
    async def create_share_link(self,path:Optional[Path]=None,files: Optional[List[CloudFile]]=None,password:str=None):
        if path:
            child_files=[await self.get_dir(path)]
        else:
            child_files=files
        if not child_files:
            logger.error(f'❌创建分享链接失败，child_files:{child_files}')
        fids=[i.id for i in child_files]
        client=await self._get_client()
        r= await client.create_share_link(fid_list=fids,password=password)
        if not r:
            logger.error(f'❌创建分享链接失败:{r}')
        logger.info(f'✅创建分享链接：{r}')
        return r


async def main():
    from app.database.database import init_db
    from app.core.logging_config import setup_logging

    await init_db()
    setup_logging()
    quark=QuarkCloudOperator("4295quark")
    await quark.create_share_link(path=Path('/资源分享/TV/China/2025/芬芳喜事/芬芳喜事'))
    # # r= await quark.ls_dir(Path('/资源分享/TvCategory.HOT_CN_DRAMA/2025/护宝寻踪'))
    # #
    # # for i in r:
    # #     print(i.name,(await i.standardized).episode_number)
    # # r= await quark.mkdir(Path('/这是新目录'))
    # movie = await movie_repository.find_by_douban_id('36455616')
    #
    # result = await quark_link_parser.parse_links([PrepareParseLinks(
    #     links=[CloudShareLink(url='https://pan.quark.cn/s/969ddab7b51e',title='赴山海')],
    #     scrape_quark_links=lazy(lambda: AsyncCachedIterator([])), movie=movie)])
    # fiter_result=await filter_flow(result)
    # for f in fiter_result:
    #     q=await f.quark_result
    #     await quark.save_file(share_files= q.share_files,parse= q.link_parse,path= Path('/这是新目录'))
    #     return
    ...
if __name__ == '__main__':
    asyncio.run(main())

