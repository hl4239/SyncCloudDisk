from typing import List

from app.database.models import EpisodesInfo
from app.modules.data_collection.interfaces.episodes_air_time_provider_interface import IEpisodesAirTimeProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.utils.lazy_load import lazy


class DefaultEpisodesAirTimeProvider(IEpisodesAirTimeProvider):
    default_time='19:00'
    async def get_air_time(self, movie_data_source: MovieDataSourceResult) -> List[EpisodesInfo]:
        for i in await movie_data_source.episodes_info:
            if not await i.air_time:
                i.air_time=lazy(self.default_time)
        return await movie_data_source.episodes_info
default_episode_air_time_provider = DefaultEpisodesAirTimeProvider()
