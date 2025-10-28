import asyncio
from abc import ABC, abstractmethod
from typing import List

from app.database.models import PanCloud, CloudType, MovieCloudInfo, Movie
from app.modules.risk_detect.schemas import RiskDetectResult
from app.modules.storage_operations.interfaces.cloud_disk_operator_interface import ICloudDiskOperator
from app.modules.storage_operations.schemas import HandleRiskFileResult


class IHandleRiskFile(ABC):



    @abstractmethod
    async def handle_(self,cloud_info: MovieCloudInfo,movie:Movie,cloud_operator:ICloudDiskOperator):
        ...

    async def handle(self,movies:List[Movie] ):
        tasks=[]
        result=[]
        for movie in movies:
            risk_cloud_infos=[i for i in (movie.cloud_infos or [])if i.is_risk_share]
            print(movie,risk_cloud_infos)
            handle_r = HandleRiskFileResult(movie=movie, handle_cloud_infos=risk_cloud_infos)
            result.append(handle_r)

            for cloud_info in risk_cloud_infos:

                operator=await ICloudDiskOperator.create_cloud_operator(cloud_info.pancloud_name)

                tasks.append(self.handle_(cloud_info,movie,operator))
        await asyncio.gather(*tasks)

        return result
