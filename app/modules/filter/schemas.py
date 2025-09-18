from typing import List, Optional
from pydantic import BaseModel, Field

from app.database.models import Movie
from app.modules.link_parse.schemas import ShareFile, LinkParse, QuarkLinkParse
from app.utils.lazy_load import Lazy, lazy


class TargetEpisode(BaseModel):
    share_files: List[ShareFile]=Field(None)
    link_parse:LinkParse=Field(None)
class TargetEpisodeFilterResult(BaseModel):
    quark_result: Optional[Lazy[TargetEpisode]]=Field(lazy(None))
    movie:Optional[Movie]=Field(None)


class FilterResult(BaseModel):
    ...