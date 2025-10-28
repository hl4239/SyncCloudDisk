from typing import List

from pydantic import BaseModel

from app.database.models import MovieCloudInfo, Movie


class RiskDetectResult(BaseModel):
    movie:Movie
    risk_cloud_infos:List[MovieCloudInfo]