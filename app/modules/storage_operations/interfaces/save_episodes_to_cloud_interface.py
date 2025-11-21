import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from app.database.models import Movie, PanCloud, CloudType, MovieCloudInfo
from app.modules.data_standard.schemas import ResourceType
from app.modules.filter.schemas import TargetEpisodeFilterResult, TargetEpisode
from app.modules.link_parse.schemas import ShareFile, LinkParse
from app.modules.storage_operations.interfaces.cloud_disk_operator_interface import ICloudDiskOperator
from app.modules.storage_operations.schemas import CloudFile
from app.modules.storage_operations.services.quark_cloud_operator import QuarkCloudOperator
from app.utils.async_iterator import AsyncCachedIterator
from app.modules.storage_operations.services.baidu_cloud_operator import BaiduCloudOperator


class ISaveEpisodesToCloud(ABC):
    @abstractmethod
    async def save_to_cloud(self,target_episode_files_iter: AsyncCachedIterator[TargetEpisode],  cloud_info: MovieCloudInfo,
                            operator: ICloudDiskOperator):
        ...

    async def _save(self,cloud_type:CloudType,target_episode_files: AsyncCachedIterator[TargetEpisode],movie:Movie):
        pan_clouds = await PanCloud.find_all().to_list()
        enable_pan_clouds = [i for i in pan_clouds if i.enable and i.cloud_type == cloud_type]

        cloud_infos = movie.cloud_infos
        cloud_info_maps = {
            i.pancloud_name: i
            for i in cloud_infos
        }
        t_cloud_infos = []
        for i in enable_pan_clouds:
            if i.name in cloud_info_maps.keys():
                t_cloud_infos.append(cloud_info_maps[i.name])
            else:
                t= MovieCloudInfo(pancloud_name=i.name, cloud_path=movie.generate_path())
                t_cloud_infos.append(t)
                cloud_infos.append(t)
        is_need_save=False
        latest_episode_info=movie.get_latest_episode_info()
        if latest_episode_info:
            latest_episode_number=latest_episode_info.episode_number
            for i in t_cloud_infos:
                if not i.latest_episode_number or i.latest_episode_number <latest_episode_number:
                    is_need_save=True
        print(is_need_save,cloud_type.name,target_episode_files)
        if is_need_save:
            if cloud_type==CloudType.QUARK:
                tasks = [
                    self.save_to_cloud(target_episode_files, cloud_info,
                                       operator=QuarkCloudOperator(cloud_info.pancloud_name)) for cloud_info in
                    t_cloud_infos]
                await asyncio.gather(*tasks)
                return
            if cloud_type==CloudType.BAIDU:
                tasks = [
                    self.save_to_cloud(target_episode_files, cloud_info,
                                       operator=BaiduCloudOperator(cloud_info.pancloud_name)) for cloud_info in
                    t_cloud_infos]
                await asyncio.gather(*tasks)
                return

    @classmethod
    async def pancloud_episode_filter(cls,pdir_file:CloudFile,operator:ICloudDiskOperator):
        result=[]
        if child:= await pdir_file.children:
            for i in child:
                st=await i.standardized
                if st.is_folder==False and(st.resource_type==ResourceType.FILE_EPISODE or st.resource_type==ResourceType.FILE_RANGE) :
                    result.append(i)
                if st.is_folder and (ResourceType.FOLDER_RANGE in st.folder_resource_type()) :
                    c1=await operator.ls_dir(st)
                    for i1 in c1:
                        st1=await i1.standardized
                        if st1.is_folder == False and (
                                st1.resource_type == ResourceType.FILE_EPISODE or st1.resource_type == ResourceType.FILE_RANGE):
                            result.append(i1)

        return result

    async def save(self,target_episode_files:List[TargetEpisodeFilterResult])->List[Movie]:
        movies=[]
        for t in target_episode_files:
            movie=t.movie



            tasks=[self._save(CloudType.QUARK,t.quark_result,t.movie),self._save(CloudType.BAIDU,t.baidu_result,t.movie)]
            await asyncio.gather(*tasks)
            movies.append(t.movie)
        return movies


