from typing import List

from app.database.models import Movie
from app.modules.link_scraping.schemes.link import LinkScrapeResult
from app.modules.link_scraping.services.pan_sou_link_scraper import pan_sou_link_scraper_service


async def  link_scrape_flow_search(movies:List[Movie],count:int) -> List[LinkScrapeResult]:
    return   await pan_sou_link_scraper_service.search(movies=movies,count=count)