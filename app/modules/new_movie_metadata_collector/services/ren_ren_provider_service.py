import asyncio
import logging
from datetime import date
from typing import List


from app.database.models import MetaDataProvider, MetaDataProviderEnum, MovieType
from app.modules.new_movie_metadata_collector.clients.renren_client import RenRenClient, renren_client
from app.modules.new_movie_metadata_collector.interfaces.new_movie_provider_interface import INewMovieProvider


logger=logging.getLogger(__name__)
class RenRenNewMovieProviderService(INewMovieProvider):
    def __init__(self,renren_client_:RenRenClient):
        self.renren_client = renren_client_
    def get_movie_type(self,renren_movie_type:str):
        if renren_movie_type=='TV':
            return MovieType.TV
        elif renren_movie_type=='MOVIE':
            return MovieType.MOVIE
        return MovieType.OTHER

    async def get_date_new_movie_metadata(self, target_date: date) -> List[MetaDataProvider]:
        data_list=  await self.renren_client.get_date_movies(target_date)
        if not data_list:
            return []
        result = []
        try:
            for i in data_list:

                result.append(MetaDataProvider(title=i['title'],provider=MetaDataProviderEnum.RENREN,id=f'{i['dramaId']}',year=f'{i["year"]}',movie_type=self.get_movie_type(i['dramaType'])))
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