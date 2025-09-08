from typing import List

from app.database.models import Movie
from app.modules.link_scraping.schemes.link import LinkScrapeResult


class LinkScrapeContext:
    def __init__(self):
        ...

    async def scrape(self,movies:List[Movie])->List[LinkScrapeResult]:
        ...
link_scrape_context=LinkScrapeContext()