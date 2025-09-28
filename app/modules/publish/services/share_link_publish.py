from typing import List

from app.database.models import Movie
from app.modules.publish.schemas import Publisher


class ShareLinkPublish:



    async def publish_to_tg(self,movies:List[Movie]):
        ...

    async def publish(self,movies:List[Movie],publisher:Publisher):
        ...