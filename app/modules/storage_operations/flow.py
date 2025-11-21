import asyncio
from pathlib import Path
from typing import List

from app.database.models import Movie, MovieCloudInfo
from app.modules.filter.schemas import TargetEpisodeFilterResult
from app.modules.storage_operations.interfaces.cloud_disk_operator_interface import ICloudDiskOperator
from app.modules.storage_operations.services.save_episodes_to_cloud import save_episodes_to_cloud_service


async def save_to_cloud_flow(target_episode_results: List[TargetEpisodeFilterResult])->List[Movie]:
    return  await save_episodes_to_cloud_service.save(target_episode_results)

async def recreate_dir(movie: Movie,cloud_infos:List[MovieCloudInfo]):
    tasks=[]
    async def i(cloud_info_: MovieCloudInfo):
        if cloud_info_.cloud_path:
            cloud_path = Path(cloud_info_.cloud_path)
            operator = await ICloudDiskOperator.create_cloud_operator(cloud_info_.pancloud_name)
            if await  operator.recreate_dir(cloud_path):
                share_link=await operator.create_share_link(cloud_path)
                cloud_info_.share_link=share_link


    for cloud_info in cloud_infos:
       tasks.append(i(cloud_info))
    await asyncio.gather(*tasks)
    return movie,cloud_infos