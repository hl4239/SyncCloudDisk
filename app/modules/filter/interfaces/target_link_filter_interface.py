from abc import ABC, abstractclassmethod, abstractmethod
from typing import List

from app.database.models import Movie
from app.modules.link_parse.schemas import LinkParseResult, LinkParse
from app.modules.link_scraping.schemes.link import LinkScrapeResult
from app.utils.async_iterator import AsyncCachedIterator
from app.utils.lazy_load import lazy


class ITargetLinkFilter(ABC):

    @abstractmethod
    async def get_target_links(self,movie:Movie,link_parses:AsyncCachedIterator[LinkParse]):
        ...

    async def filter(self,link_parse_results:List[LinkParseResult])->List[LinkParseResult]:
        results=[]
        for link_scrape_result in link_parse_results:
            target_link_result=LinkParseResult(quark_parses=AsyncCachedIterator(self.get_target_links(link_scrape_result.movie,link_scrape_result.quark_parses)),
                                                      movie=link_scrape_result.movie)

            results.append(target_link_result)
        return results
