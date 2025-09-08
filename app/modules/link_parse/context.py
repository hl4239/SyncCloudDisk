from typing import List

from app.modules.link_parse.schemas import LinkParseResult


class LinkParseContext:
    def __init(self):
        ...
    async def parse(self,link_scrape_datas:List[LinkParseResult])->List[LinkParseResult]:
        ...
link_parse_context=LinkParseContext()