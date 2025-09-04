from abc import ABC, abstractmethod

from app.database.models import Movie


class ITotalEpisodesProvider(ABC):
    @abstractmethod
    async def get_total_episodes(self,movie:Movie)->str:
        """
        获取影视的总剧集
        :param keyword:
        :return:
        """
        ...

