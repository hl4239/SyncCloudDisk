import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any

from app.database.models import Movie, PanCloud, CloudType, MovieCloudInfo
from app.modules.filter.schemas import TargetEpisodeFilterResult, TargetEpisode
from app.modules.link_parse.schemas import ShareFile, LinkParse
from app.modules.storage_operations.clients.quark_cloud_client import get_quark_cloud_client
from app.modules.storage_operations.interfaces.cloud_disk_operator_interface import ICloudDiskOperator
from app.modules.storage_operations.schemas import CloudFile
from app.modules.storage_operations.services.quark_cloud_operator import QuarkCloudOperator
from app.utils.async_iterator import AsyncCachedIterator
from app.utils.lazy_load import Lazy


class ISaveEpisodesToCloud(ABC):
    @abstractmethod
    async def save_to_cloud(self, share_files: List[ShareFile], parse: LinkParse, cloud_info: MovieCloudInfo,
                            base_path: Path, operator: ICloudDiskOperator):
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
                t= MovieCloudInfo(pancloud_name=i.name, pdir_name=movie.title_season)
                t_cloud_infos.append(t)
                cloud_infos.append(t)
        is_need_save=False
        latest_episode_number=movie.get_latest_episode_info().episode_number
        for i in t_cloud_infos:
            if not i.latest_episode_number or i.latest_episode_number <latest_episode_number:
                is_need_save=True
        if is_need_save:
            if cloud_type==CloudType.QUARK:
                async for tt in  target_episode_files:
                    tasks=[self.save_to_cloud(tt.share_files,tt.link_parse,cloud_info,base_path=movie.generate_path(),operator=QuarkCloudOperator(cloud_info.pancloud_name)) for cloud_info in t_cloud_infos]
                    await asyncio.gather(*tasks)
                    return

    @classmethod
    async def pancloud_episode_filter(cls,pdir_file:CloudFile):
        result=[]
        if child:= await pdir_file.children:
            for i in child:
                st=await i.standardized
                if st.episode_number:
                    result.append(i)
        return result

    async def save(self,target_episode_files:List[TargetEpisodeFilterResult])->List[Movie]:
        movies=[]
        for t in target_episode_files:
            movie=t.movie


            await self._save(CloudType.QUARK,t.quark_result,t.movie)
            movies.append(t.movie)
        return movies


