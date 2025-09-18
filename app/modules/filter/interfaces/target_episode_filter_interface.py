import logging
from abc import ABC, abstractmethod
from typing import List

from app.database.models import Movie
from app.modules.filter.schemas import TargetEpisode, TargetEpisodeFilterResult
from app.modules.link_parse.schemas import LinkParseResult, LinkParse
from app.utils.async_iterator import AsyncCachedIterator
from app.utils.lazy_load import lazy

logger=logging.getLogger(__name__)
class ITargetEpisodeFilter(ABC):
    @abstractmethod
    async def get_target_episode(self, movie: Movie, link_parses: AsyncCachedIterator[LinkParse]):
        ...

    async def filter(self, link_parse_results: List[LinkParseResult]) -> List[TargetEpisodeFilterResult]:
        results = []
        for link_scrape_result in link_parse_results:
            logger.debug(f'开始注册target_episode_filter: {link_scrape_result.movie.title_season}')
            target_link_result = TargetEpisodeFilterResult(quark_result=
                                                  lazy(lambda i=link_scrape_result.movie,j=link_scrape_result.quark_parses: self.get_target_episode(i,
                                                                          j)),
                                               movie=link_scrape_result.movie)

            results.append(target_link_result)
        return results
