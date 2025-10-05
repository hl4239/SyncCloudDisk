import copy
import logging
from abc import abstractmethod, ABC
from typing import List

from app.database.models import EpisodesInfo, MovieType
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.services.movie_service import movie_service
from app.utils.lazy_load import lazy

logger=logging.getLogger(__name__)
class IEpisodesAirTimeProvider(ABC):
    @abstractmethod
    async def get_air_time(self,movie_data_source:MovieDataSourceResult) ->  List[EpisodesInfo]:
        ...

    async def   set_air_time(self,movie_data_result:MovieDataSourceResult):
        """
        在已有的 list episodes_info 中对air_time补充
        :param movie_data_result:
        :return:
        """
        copy_movie_data = copy.deepcopy(movie_data_result)
        movie_data_result.episodes_info = lazy(lambda c=copy_movie_data: self.get_air_time(c))

