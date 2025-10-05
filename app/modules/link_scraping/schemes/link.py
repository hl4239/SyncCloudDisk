import asyncio

from pydantic import BaseModel, Field
from typing import Optional, List


from app.database.models import Movie, CloudShareLink
from app.utils.async_iterator import AsyncCachedIterator
from app.utils.lazy_load import Lazy, lazy




class LinkScrapeResult(BaseModel):
    quark_links: Optional[Lazy[AsyncCachedIterator[CloudShareLink]]] = Field(default_factory=lambda: lazy(None),description='')
    movie:Optional[Movie]=Field(None,description='')

async def main():
    async def links_provider_example(params)->AsyncCachedIterator[CloudShareLink]:
        print(params)
        await asyncio.sleep(1)
        yield CloudShareLink(url='link1',title='asd',share_password='<PASSWORD>')
        await asyncio.sleep(1)
        yield CloudShareLink(url='link2', title='asd2', share_password='<PASSWORD>')
    async def links_provider_example2(params)->List[CloudShareLink]:
        return [CloudShareLink(url='link1', title='asd', share_password='<PASSWORD>'),]

    link_results=[]
    for i in range(5):
        link_result=LinkScrapeResult(quark_links=lazy(AsyncCachedIterator(links_provider_example2(i))),movie=None)
        link_results.append(link_result)
    for link_result in link_results:

        async for l in await link_result.quark_links:
            print(l.title)
        async for l in await link_result.quark_links:
            print(l.title)
if __name__ == '__main__':
    asyncio.run(main())