import asyncio
from typing import List

from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import EpisodesInfo, MovieType
from app.modules.data_collection.interfaces.episodes_infos_provider_interface import IEpisodesInfosProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.movie_service import movie_service


class EpisodesInfoProviderService(IEpisodesInfosProvider):
    async def get_episodes_infos(self, movie_data_source: MovieDataSourceResult) -> List[EpisodesInfo]:
        episodes_infos=await movie_data_source.episodes_info
        total_episodes=await movie_data_source.total_episodes
        aliases=await movie_data_source.aliases
        if episodes_infos is None:
            episodes_infos=await movie_service.create_episodes_info(total_episodes,movie_service.get_episode_range(total_episodes,aliases))
        exited_episode_number=[
            e.episode_number
            for e in episodes_infos
        ]
        all_episodes_infos=await movie_service.create_episodes_info(total_episodes,movie_service.get_episode_range(total_episodes,aliases))
        for e in all_episodes_infos:
            if e.episode_number not in exited_episode_number:
                episodes_infos.append(e)
        return episodes_infos

episodes_info_provider_service = EpisodesInfoProviderService()

async def main():
    from app.utils.lazy_load import lazy
    from app.modules.data_collection.flow import registry_movie_data_sources
    await init_db()
    setup_logging()
    m=await registry_movie_data_sources([('36779574',MovieType.TV)])
    r= await episodes_info_provider_service.get_episodes_infos(m)
    print(r)
if __name__ == '__main__':
    asyncio.run(main())