from typing import Optional

from pydantic import BaseModel, Field


class EpisodeNormalized(BaseModel):
    original_name: Optional[str] = Field()
    normalized_name: Optional[str] = Field(pattern=r'^(\d{2}|\d{2}-\d{2})$')
    is_valid:bool=False

if __name__== '__main__':
    n=EpisodeNormalized(original_name=None, normalized_name='12-11')
    print(n)
