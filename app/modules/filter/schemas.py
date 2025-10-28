from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.database.models import Movie
from app.modules.link_parse.schemas import ShareFile, LinkParse, QuarkLinkParse
from app.modules.storage_operations.schemas import CloudFile
from app.utils.async_iterator import AsyncCachedIterator


class TargetEpisode(BaseModel):
    share_files: List[ShareFile|CloudFile]=Field(None)
    link_parse:LinkParse=Field(None)
class TargetEpisodeFilterResult(BaseModel):
    quark_result: Optional[AsyncCachedIterator[TargetEpisode]]=Field(AsyncCachedIterator([]))
    baidu_result: Optional[AsyncCachedIterator[TargetEpisode]] = Field(AsyncCachedIterator([]))
    movie:Optional[Movie]=Field(None)
    model_config = ConfigDict(arbitrary_types_allowed=True)

class FilterResult(BaseModel):
    ...