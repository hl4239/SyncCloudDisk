from abc import ABC, abstractmethod

from app.modules.link_parse.schemas import ShareItem
from app.modules.link_scraping.schemes.link import ResourceLink


class IEpisodeStandardizer(ABC):
    @abstractmethod
    async def standardize(self, share:ShareItem) -> ShareItem:
        ...