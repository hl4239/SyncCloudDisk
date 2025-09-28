from abc import ABC, abstractmethod
from datetime import date
from typing import List

from app.database.models import Movie, MetaDataProviderEnum, MetaDataProvider




class INewMovieProvider(ABC):

    @abstractmethod
    async def get_date_new_movie_metadata(self, target_date: date)->List[MetaDataProvider]:
        ...

    async def get_today_new_movie_metadata(self,)->List[MetaDataProvider]:
        return await self.get_date_new_movie_metadata(date.today())








