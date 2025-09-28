import asyncio
import logging
from datetime import date
from typing import List

from pydantic import BaseModel

from app.database.models import MetaDataProvider, MetaDataProviderEnum
from app.modules.new_movie_metadata_collector.clients.renren_client import RenRenClient, renren_client
from app.modules.new_movie_metadata_collector.interfaces.new_movie_provider_interface import INewMovieProvider


logger=logging.getLogger(__name__)
class RenRenNewMovieProviderService(INewMovieProvider):
    def __init__(self,renren_client_:RenRenClient):
        self.renren_client = renren_client_
    async def get_date_new_movie_metadata(self, target_date: date) -> List[MetaDataProvider]:
        json_resp=  await self.renren_client.get_date_movies(target_date)
        if not json_resp:
            return []
        result = []
        try:
            for i in json_resp['data']['content']:
                result.append(MetaDataProvider(title=i['title'],provider=MetaDataProviderEnum.RENREN,id=f'{i['dramaId']}'))
            return result
        except Exception as e:
            logger.error(f'{e}',exc_info=True)
        return []
renren_new_movie_provider_service = RenRenNewMovieProviderService(renren_client_=renren_client)
async def main():
    r=    await renren_new_movie_provider_service.get_today_new_movie_metadata()
    print(r)
if __name__ == '__main__':
    asyncio.run(main())