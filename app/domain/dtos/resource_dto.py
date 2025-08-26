from typing import Optional, List
from pydantic import BaseModel
import datetime

class AccountDTO(BaseModel):
    name: Optional[str] = None
    cloud_storage_path: Optional[str] = None
    create_share_link: Optional[str] = None
    last_sync_share_links: List[str] = []
    is_sync_finish: bool = False

class EpisodesInfoDTO(BaseModel):
    total_episodes: Optional[str] = None
    season: Optional[str] = None
    episodes_url: Optional[str] = None
    last_update_time: Optional[datetime.datetime] = None

class CloudDiskInfoDTO(BaseModel):
    last_sync_share_link: Optional[str] = None
    accounts: List[AccountDTO] = []

class ResourceDTO(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    tv_category: Optional[str] = None
    image_path: Optional[str] = None
    tags: List[str] = []
    last_metadata_update_time: Optional[datetime.datetime] = None
    episodes_info: Optional[EpisodesInfoDTO] = None
    cloud_disk_info: Optional[CloudDiskInfoDTO] = None

def resource_to_dto(resource):
    return ResourceDTO(
        id=resource.id,
        title=resource.title,
        subtitle=resource.subtitle,
        description=resource.description,
        tv_category=str(resource.tv_category) if resource.tv_category else None,
        image_path=resource.image_path,
        tags=resource.tags,
        last_metadata_update_time=resource.last_metadata_update_time,
        episodes_info=EpisodesInfoDTO(**resource.episodes_info.dict()) if resource.episodes_info else None,
        cloud_disk_info=CloudDiskInfoDTO(
            last_sync_share_link=resource.cloud_disk_info.last_sync_share_link if resource.cloud_disk_info else None,
            accounts=[AccountDTO(**acc.dict()) for acc in resource.cloud_disk_info.accounts] if resource.cloud_disk_info and resource.cloud_disk_info.accounts else []
        ) if resource.cloud_disk_info else None
    )
