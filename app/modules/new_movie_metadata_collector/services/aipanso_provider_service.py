import asyncio
import logging
from datetime import date
from typing import List


from app.database.models import MetaDataProvider, MetaDataProviderEnum, MovieType
from app.modules.new_movie_metadata_collector.clients.aipanso_client import AipansouClient, aipanso_client
from app.modules.new_movie_metadata_collector.clients.renren_client import RenRenClient, renren_client
from app.modules.new_movie_metadata_collector.interfaces.new_movie_provider_interface import INewMovieProvider


logger=logging.getLogger(__name__)
class AiPanSoProviderService(INewMovieProvider):
    def __init__(self, aipanso_client: AipansouClient):
        self.aipanso_client = aipanso_client

    async def get_date_new_movie_metadata(self, target_date: date) -> List[MetaDataProvider]:
        pass



    async def get_today_new_movie_metadata(self) -> List[MetaDataProvider]:
        keys= await self.aipanso_client.get_hot_key()
        result = []
        for key in keys:
            result.append(MetaDataProvider(title=key))
        return result

aipanso_new_movie_provider_service = AiPanSoProviderService(aipanso_client=aipanso_client)
async def main():
    r=    await aipanso_new_movie_provider_service.get_today_new_movie_metadata()
    print(r)
if __name__ == '__main__':
    asyncio.run(main())