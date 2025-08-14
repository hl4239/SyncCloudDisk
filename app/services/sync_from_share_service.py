import logging
from typing import Union, Optional, List
from multipledispatch import dispatch

from app.domain.models.cloud_file import ShareFile, CloudFile
from app.services.cloud_disk_service import CloudDiskService
from app.services.cloud_file_service import CloudFileService
from app.services.cloud_share_service import CloudShareService
from app.services.episode_normalize_service import EpisodeNormalizeService
from app.services.resource_service import ResourceService

logger=logging.getLogger()
class SyncFromShareService:

    def __init__(self, cloud_disk_service: CloudDiskService, cloud_share_service: CloudShareService,
                 normalize_service: EpisodeNormalizeService, cloud_file_service: CloudFileService):
        self.cloud_disk_service = cloud_disk_service
        self.cloud_share_service = cloud_share_service
        self.normalize_service = normalize_service
        self.cloud_file_service = cloud_file_service

    # 使用 dispatch 装饰器创建重载方法
    @dispatch(list, list)
    def get_new_files(
            self,
            share_files: List[CloudFile],
            existed_files: List[CloudFile]
    ) -> List[CloudFile]:
        """
        从两个 CloudFile 列表中找出分享列表中新增的剧集。
        重载版本1: 直接处理两个文件列表
        """
        existed_norm_names = [f.normalized_name for f in existed_files]
        share_norm_names = [f.normalized_name for f in share_files]

        share_file_map = {f.normalized_name: f for f in share_files}

        new_episode_nums = self.normalize_service.is_collection_episode_in_other_collection(
            existed_norm_names, share_norm_names)

        new_episode_names = self.normalize_service.find_collection_episode_by_list_num(
            new_episode_nums, share_norm_names)

        return [share_file_map[name] for name in new_episode_names]



    @dispatch(str, str, str, bool, bool)
    async def get_new_files(
            self,
            name_type: str,
            path: str,
            share_link: str,
            cloud_refresh: bool = False,
            share_refresh: bool = False
    ):
        """

        """


        parse_result = await self.cloud_share_service.get_parse_info(
            share_link, is_normalize=True, refresh=share_refresh)

        if not parse_result.is_valid:
            return [],parse_result

        root_cloud_share_file = parse_result.root
        share_files = root_cloud_share_file.flatten()
        normalized_share_files = await self.cloud_share_service.get_normalized_files(share_files)

        cloud_files = await self.cloud_disk_service.ls_dir(
            path=path, name_type=name_type, refresh=cloud_refresh)

        await self.cloud_file_service.normalize_episode(cloud_files)
        normalized_cloud_files = await self.cloud_file_service.get_normalized_files(cloud_files)

        return self.get_new_files(normalized_share_files, normalized_cloud_files),parse_result

    async def sync_new_file(self, name_type, path, share_link,share_refresh=False):
        """
        同步新文件的方法
        """
        new_files,parse_result = await self.get_new_files(name_type, path, share_link,True,share_refresh)

        await self.cloud_disk_service.save_from_share(share_parse_info=parse_result,share_files=new_files,path=path,name_type=name_type)

        return new_files

    async def is_synced_latest(self, name_type:str, path:str,total_episodes:str):
        cloud_files=await self.cloud_disk_service.ls_dir(path=path, name_type=name_type, refresh=True)
        await self.cloud_file_service.normalize_episode(cloud_files)
        normalized_cloud_files = await self.cloud_file_service.get_normalized_files(cloud_files)
        cloud_file_names=[
            f.normalized_name
            for f in normalized_cloud_files
        ]
        normalized_total_episodes=(await self.normalize_service.generate_name([total_episodes]))[0]
        if normalized_total_episodes.is_valid:
            f= self.normalize_service.is_collection_episode_in_other_collection(cloud_file_names,[normalized_total_episodes.normalized_name])
            result=False
            if len(f)==0:

                result= True
        else:
            raise Exception(f'total_episodes标准化错误')
        logger.debug(f'{name_type} 最新剧集的同步 : {result} - {f}')
        return result

