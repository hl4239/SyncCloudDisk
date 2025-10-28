from abc import abstractmethod, ABC
from typing import List

from app.modules.link_parse.schemas import LinkParseResult, PrepareParseLinks
from app.utils.async_iterator import AsyncCachedIterator


class ILinkParser(ABC):
    @abstractmethod
    async def parse_quark(self, link_scrape_result: PrepareParseLinks):
        ...
    @abstractmethod
    async def parse_baidu(self, link_scrape_result: PrepareParseLinks):
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
                                     baidu_parses=AsyncCachedIterator(self.parse_baidu(link)),
                                      movie=link.movie

                                     )

            results.append(result)
        return results


