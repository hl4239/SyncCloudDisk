from typing import Optional, Union, List, AsyncIterable, AsyncIterator, Callable

from pydantic import BaseModel, Field, ConfigDict

from app.utils import AsyncCachedIterator


class ShareLinkCrawlerResults(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: Optional[str] = None
    source: Optional[str] = None
    share_links: Union[List[str], AsyncIterator[str]] = Field(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        self._cached_iter = AsyncCachedIterator(self.share_links)

    def __aiter__(self):
        return self._cached_iter.__aiter__()