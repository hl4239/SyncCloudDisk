from abc import abstractmethod, ABC

from app.modules.link_parse.schemas import ShareItem
from app.modules.link_scraping.schemes.link import ResourceLink


class ILinkParser(ABC):
    @abstractmethod
    async def parse(self, link: ResourceLink) ->ShareItem:
        ...

