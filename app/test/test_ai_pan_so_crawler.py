import pytest

from app.infrastructure.containers import Container

@pytest.mark.asyncio
async def test_search():
    container=Container()
    aipanso_crawler =container.aipanso_crawler()
    results= await aipanso_crawler.search('藏海传',2)
    async for result in results:
        print(result)
        break
    async  for result in results:
        print(result)


