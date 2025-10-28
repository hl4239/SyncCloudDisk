from abc import ABC, abstractmethod
from typing import List

from app.database.models import Movie
from app.modules.link_parse.schemas import LinkParseResult, LinkParse
from app.utils.async_iterator import AsyncCachedIterator


class ITargetLinkFilter(ABC):

    @abstractmethod
    async def get_target_links(self,movie:Movie,link_parses:AsyncCachedIterator[LinkParse]):
        ...

    async def filter(self,link_parse_results:List[LinkParseResult])->List[LinkParseResult]:
        results=[]
        for link_scrape_result in link_parse_results:
            target_link_result=LinkParseResult(quark_parses=AsyncCachedIterator(self.get_target_links(link_scrape_result.movie,link_scrape_result.quark_parses)),
                                               baidu_parses=AsyncCachedIterator(self.get_target_links(link_scrape_result.movie,link_scrape_result.baidu_parses)),
                                                      movie=link_scrape_result.movie)

            results.append(target_link_result)
        return results
