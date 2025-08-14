from abc import ABC, abstractmethod

from app.infrastructure.config import CloudAPIType


class ShareLinkCrawler(ABC):
    def __init__(self):
        pass
    @abstractmethod
    async def search(self, keyword: str, num: int,cloud_type:CloudAPIType):
        ...


