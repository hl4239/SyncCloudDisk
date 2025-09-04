from abc import ABC, abstractmethod

from app.database.models import Movie


class ICurrentEpisodesProvider(ABC):
    @abstractmethod
    async def get_current_episodes(self,movie:Movie)->str:
        """
        获取影视当前更新的剧集
        :param movie:
        :return:
        """
        ...