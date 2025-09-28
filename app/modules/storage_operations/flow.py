from typing import List

from app.database.models import Movie
from app.modules.filter.schemas import TargetEpisodeFilterResult
from app.modules.storage_operations.services.save_episodes_to_cloud import save_episodes_to_cloud_service


async def save_to_cloud_flow(target_episode_results: List[TargetEpisodeFilterResult])->List[Movie]:
    return  await save_episodes_to_cloud_service.save(target_episode_results)
