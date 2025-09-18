import copy
from abc import abstractmethod, ABC
from typing import List

from app.modules.link_parse.schemas import LinkParseResult, PrepareParseLinks
from app.modules.link_scraping.schemes.link import  LinkScrapeResult
from app.utils.async_iterator import AsyncCachedIterator
from app.utils.lazy_load import lazy


class ILinkParser(ABC):
    @abstractmethod
    async def parse_quark(self, link_scrape_result: PrepareParseLinks):
        ...


    async def parse_links(self,links:List[PrepareParseLinks])->List[LinkParseResult]:
        """
        多个movie
        每个movie不同的网盘有多个link
        :param links:
        :return:
        """
        results = []
        for link in links:
            result = LinkParseResult(quark_parses=AsyncCachedIterator(self.parse_quark(link)),
                                      movie=link.movie)
            results.append(result)
        return results


