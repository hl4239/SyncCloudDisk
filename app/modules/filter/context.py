from typing import List

from app.modules.filter.schemas import EpisodesFilterResult
from app.modules.link_scraping.schemes.link import LinkScrapeResult


class EpisodesFilterContext:
    def __init__(self):
        ...
    async def get_new_episodes(self,link_parse_results:List[LinkScrapeResult])->List[EpisodesFilterResult]:
        ...
episodes_filter_context=EpisodesFilterContext()