import logging
from typing import Callable, Optional

from sqlalchemy.util import await_only

from app.domain.models.cloud_file import CloudFile, ShareParseInfo, QuarkShareFile, QuarkShareParseInfo
from app.infrastructure.cloud_storage.cloud_api_factory import CloudAPIFactory
from app.infrastructure.config import Settings, CloudAPIConfig, CloudAPIType
from app.services.cloud_file_service import CloudFileService

logger=logging.getLogger()
class CloudDiskService:
    def __init__(self,config:list[CloudAPIConfig],cloud_api_factory:CloudAPIFactory,cloud_file_service:CloudFileService,):
        self.cloud_api_factory=CloudAPIFactory
        self.cloud_api_config=config
        # 对应网盘的根节点cloud_file
        self.cloud_file_dict={}
        self.cloud_file_service=cloud_file_service




    async def fetch_dir_info(self,pdir_path_list:[str],name_type):
        """
        根据路径获取指定目录,未获取到则返回None
        :param pdir_path_list:
        :param name_type:
        :return:
        """

        cloud_api=self.cloud_api_factory.get_by_key(name_type)
        try:

            resp_json=await cloud_api.get_fids(pdir_path_list)
        except Exception as e:
            logger.debug(f'从网盘获取目录信息失败:error:{e}')
            return None
        logger.debug(f'从网盘获取目录信息:{resp_json}')
        result = []
        for i in resp_json:
            cloud_file = CloudFile(
                fid=i["fid"],
                file_name=i["file_name"],
                pdir_fid=i["pdir_fid"],
                file_type=i["file_type"],
                children=None

            )
            result.append(cloud_file)
        return result

    async def fetch_dir_children(self,pdir_fid:str,name_type):
        cloud_api = self.cloud_api_factory.get_by_key(name_type)

        resp_json = await cloud_api.ls_dir(pdir_fid)
        result = []

        for i in resp_json:
            cloud_file = CloudFile(
                fid=i["fid"],
                file_name=i["file_name"],
                pdir_fid=i["pdir_fid"],
                file_type=i["file_type"],
                children=None

            )
            result.append(cloud_file)
        return result

    def _traverse(
            self,
            path: str,
            name_type: str,
            create_missing:bool=False,
            leaf_cloud_file:Optional[CloudFile]=None
    ) :
        """
        遍历指定的路径


        :param path: 要遍历的路径，如 '/dir1/dir2/dir3'
        :param name_type: 网盘标识(如"quark-4295")
        :param create_missing:创建路径中间不存在的目录
        :param leaf_cloud_file:对叶节点网盘相关的字段更新
        :return: 如果找到返回对象 否则返回None
        """
        root=self.cloud_file_dict[name_type]

        return root.traverse(path=path,create_missing=create_missing,leaf_cloud_file=leaf_cloud_file)

    async def ls_dir(self,path:str,name_type:str,refresh:bool=False):
        """
        根据name_type从cloud_file_dict中获取对应网盘的根节点cloud_file，然后进行遍历，
        :param refresh: 是否调用cloud_api刷新缓存
        :param name_type: 格式为：网盘类型-手机尾号，如quark-4295
        :param path: /dir1/dir2/dir3

        :return:
        """
        pdir_cloud_file= self._traverse(path,name_type,create_missing=False,leaf_cloud_file=None)
        if pdir_cloud_file is None or pdir_cloud_file.children is None or refresh:

            if pdir_cloud_file is not None and pdir_cloud_file.fid is not None:

                pdir_fid=pdir_cloud_file.fid
                logger.debug(f'找到"{path}的缓存,取得fid={pdir_fid}')
                result=await self.fetch_dir_children(pdir_fid,name_type)
            else:
                logger.debug(f'未找到"{path}的缓存,正在从网盘获取...')
                new_pdir_cloud_file= (await self.fetch_dir_info(pdir_path_list=[path],name_type=name_type))[0]
                pdir_cloud_file=new_pdir_cloud_file
                pdir_fid=new_pdir_cloud_file.fid
                logger.debug(f'从网盘获取fid={pdir_fid}')
            result=await self.fetch_dir_children(pdir_fid,name_type)
            pdir_cloud_file.children = result

            self._traverse(path=path, name_type=name_type, create_missing=True, leaf_cloud_file=pdir_cloud_file)
            logger.debug(f'从网盘api获取并更新缓存“{path}”：{result}')
        else:

            result=pdir_cloud_file.children
            logger.debug(f'从缓存中返回"{path}"children:{result}')
        return result

    async def get_dir_info(self,path:str,name_type:str,refresh:bool=False):
        pdir_cloud_file = self._traverse(path, name_type, create_missing=False, leaf_cloud_file=None)
        if pdir_cloud_file is None or pdir_cloud_file.fid is  None or refresh:
            new_pdir_cloud_file = (await self.fetch_dir_info(pdir_path_list=[path], name_type=name_type))[0]
            pdir_cloud_file = new_pdir_cloud_file
            self._traverse(path, name_type, create_missing=True, leaf_cloud_file=pdir_cloud_file)
        return pdir_cloud_file

    async def is_existed(self,path:str,name_type:str):

        f =await self.fetch_dir_info(pdir_path_list=[path], name_type=name_type)
        if f is not None and len(f)>0:
            self._traverse(path=path, name_type=name_type, create_missing=True, leaf_cloud_file=f[0])
            return True
        return False

    async def mkdir(self,path:str,name_type:str):

        cloud_api=self.cloud_api_factory.get_by_key(name_type)
        logger.debug(f'正在创建目录,path={path},name_type={name_type}')
        if await self.is_existed(path=path,name_type=name_type):
            logger.debug(f'目录已存在,path={path},name_type={name_type}')
            return True
        try:
            await cloud_api.mkdir(path)
            logger.debug(f'目录创建成功，path={path},name_type={name_type}')
            return True

        except Exception as e:

            logger.debug(f'目录创建失败,path={path},name_type={name_type},error={e}')
            return False

    async def save_from_share(self, share_parse_info:ShareParseInfo, share_files: list[CloudFile],path:str,name_type:str):
        if share_files is None or len(share_files)==0 :
            return  True

        if not await self.mkdir(path,name_type=name_type):
            logger.error(f'转存时创建文件夹失败：path={path},name_type={name_type}')
            return False

        to_pdir_cloud_file=await self.get_dir_info(path=path,name_type=name_type)

        cloud_api=self.cloud_api_factory.get_by_key(name_type)
        f=share_files[0]
        if isinstance(f,QuarkShareFile) and isinstance(share_parse_info,QuarkShareParseInfo):
            fids=[f.fid for f in share_files]
            fid_tokens=[f.share_fid_token for f in share_files]
            await cloud_api.save_file(fid_list=fids,fid_token_list=fid_tokens,pwd_id=share_parse_info.pwd_id,stoken=share_parse_info.stoken,to_pdir_fid=to_pdir_cloud_file.fid)
            return True

    async def create_share_link(self,name_type:str,title:Optional[str]=None,path:Optional[str]=None,cloud_files:list[CloudFile]=None):
        """
        如果path不为None则忽略cloud_files参数
        :param title:
        :param path:
        :param cloud_files:
        :param name_type:
        :return:
        """
        if path is not None:
            cloud_files=[await self.get_dir_info(path=path,name_type=name_type)]
        cloud_api=self.cloud_api_factory.get_by_key(name_type)
        if cloud_files is None or len(cloud_files)==0:
            return None

        return  await cloud_api.create_share_link(fid_list=[f.fid for f in cloud_files],title=title)


    async def init(self):
        await self.init_cloud_api()

    async def init_cloud_api(self):
        """
        初始化所有的
        :return:
        """
        for config in self.cloud_api_config:
            cloud_api,name_type =await self.cloud_api_factory.init_cloud_api(config)
            self.cloud_file_dict.update({
                name_type: cloud_api.get_root_info()
            })







