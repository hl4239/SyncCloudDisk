import copy
from abc import ABC, abstractmethod
from typing import List


from app.database.models import Movie, CloudShareLink
from app.modules.link_scraping.schemes.link import LinkScrapeResult
from app.utils.async_iterator import AsyncCachedIterator
from app.utils.lazy_load import lazy


class ILinkScraper(ABC):


    @abstractmethod
    async def search_quark(self,movie:Movie,count:int) -> AsyncCachedIterator[CloudShareLink]:
        ...
    @abstractmethod
    async def search_baidu(self, movie: Movie, count: int) -> AsyncCachedIterator[CloudShareLink]:
        ...


    async def search( self,movies:List[Movie],count:int) ->List[LinkScrapeResult]:
        """

        :param movies:
        :param count: 每个影视爬取的网盘链接个数
        :return:
        """
        results= []
        for movie in movies:
            copy_movie=copy.deepcopy(movie)
            result= LinkScrapeResult(quark_links=lazy(lambda i=copy_movie,j=count:self.search_quark(i,j)),
                                     baidu_links=lazy(lambda i=copy_movie,j=count:self.search_baidu(i,j)),

                                     movie=movie)
            results.append(result)
        return results





