from typing import List

from app.modules.link_parse.schemas import PrepareParseLinks
from app.modules.link_parse.services.quark_link_parser import quark_link_parser
from app.modules.link_scraping.schemes.link import LinkScrapeResult


async def link_parse_flow_parses(links:List[PrepareParseLinks]):
    result= await quark_link_parser.parse_links(links)
    return result