from abc import ABC
from typing import List

from app.modules.filter.schemas import EpisodesFilterResult
from app.modules.link_scraping.schemes.link import LinkScrapeResult


class INewEpisodesFilter(ABC):
    async def get_new_episodes(self,link_parse_results:List[LinkScrapeResult])->List[EpisodesFilterResult]:
        ...