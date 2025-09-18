from typing import List

from app.database.models import EpisodesInfo
from app.modules.data_collection.interfaces.episodes_infos_provider_interface import IEpisodesInfosProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.movie_service import movie_service


class EpisodesInfoProviderService(IEpisodesInfosProvider):
    async def get_episodes_infos(self, movie_data_source: MovieDataSourceResult) -> List[EpisodesInfo]:
        episodes_infos=await movie_data_source.episodes_info
        total_episodes=await movie_data_source.total_episodes
        if episodes_infos is None:
            episodes_infos=movie_service.create_episodes_info(total_episodes)
        exited_episode_number=[
            e.episode_number
            for e in episodes_infos
        ]
        all_episodes_infos=movie_service.create_episodes_info(total_episodes)
        for e in all_episodes_infos:
            if e.episode_number not in exited_episode_number:
                episodes_infos.append(e)
        return episodes_infos

episodes_info_provider_service = EpisodesInfoProviderService()