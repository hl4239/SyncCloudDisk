from typing import List

from pydantic import BaseModel

from app.database.models import Movie
from app.modules.link_parse.schemas import  ShareItem
from app.modules.link_scraping.schemes.link import LinkScrapeResult

class EpisodesFilterItem(BaseModel):
    cloud_unique:str
    episodes_for_update: List[ShareItem]


class EpisodesFilterResult(BaseModel):
    movie:Movie
    link_inspection_result:LinkScrapeResult
    episodes_for_update:List[ShareItem]