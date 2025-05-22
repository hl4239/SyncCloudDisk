from openai import BaseModel
from typing_extensions import Optional


class Crawler:
    def __init__(self):
        pass

class ResourceMetadata(BaseModel):
    latest_episode:Optional[str]
    episodes_url:Optional[str]

class SearchResults(BaseModel):
    title:str
    resource_metadata:ResourceMetadata