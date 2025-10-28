from typing import List

from app.modules.link_parse.schemas import PrepareParseLinks
from app.modules.link_parse.services.link_parser import link_parser


async def link_parse_flow_parses(links:List[PrepareParseLinks]):
    result= await link_parser.parse_links(links)
    return result