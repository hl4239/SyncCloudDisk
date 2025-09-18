import asyncio
import logging

from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import CloudShareLink, CloudType, Movie, TMDBInfos, MovieType
from app.modules.data_standard.schemas import StandardizedResult
from app.modules.data_standard.services.regex_standardizer import regex_standardizer
from app.modules.link_parse.clients.quark_parse_client import QuarkParseClient
from app.modules.link_parse.interfaces.link_parser_interface import ILinkParser
from app.modules.link_parse.schemas import ShareFile, FileType, QuarkLinkParse, PrepareParseLinks
from app.modules.link_scraping.schemes.link import LinkScrapeResult
from app.utils.async_iterator import AsyncCachedIterator, AsyncMergedCachedIterator
from app.utils.lazy_load import lazy

logger=logging.getLogger(__name__)
class QuarkLinkPaser(ILinkParser):
    @classmethod
    async def _quark_get_dir(cls,pdir_fid:str,quark_client:QuarkParseClient,movie:Movie):

        ls_resp=await quark_client.ls_dir(pdir_fid)
        result=[]
        if file_list:=ls_resp.get('list'):

            for file in file_list:
                name=file.get('file_name')
                id_=file.get('fid')
                type_ = FileType.FOLDER if file.get("file_type") == 0 else FileType.FILE
                share_file=ShareFile(name=name,id=id_,type=type_,parent_id=pdir_fid)

                result.append(share_file)
            season_number = movie.get_season_number()
            standardized_results = [StandardizedResult(original_name=f.name, season_number=season_number,is_folder=f.is_folder) for
                                    f in result]
            for f in result:
                f.standardized=lazy(lambda i=name:regex_standardizer.get_standardized_result(target_original=i,items=standardized_results))
                if f.is_folder:
                    f.children = lazy(lambda: cls._quark_get_dir(id_, quark_client, movie))



        logger.debug(f'获取pdir_fid={pdir_fid}目录,result={result}')
        return result





    async def parse_quark(self,prepare_parse_links:PrepareParseLinks):

        links_quark=[link for link in prepare_parse_links.links if link.type==CloudType.QUARK]
        scrape_quark_links=await prepare_parse_links.scrape_quark_links
        movie= prepare_parse_links.movie
        async for quark_link in AsyncMergedCachedIterator([links_quark,scrape_quark_links]):
            quark_parse_client=QuarkParseClient(quark_link.url)
            parse_result=await quark_parse_client.parse_share_link()
            if parse_result.get('ok'):
                pwd_id=parse_result.get('pwd_id')
                passcode=parse_result.get('passcode')
                pdir_fid=parse_result.get('pdir_fid')
                stoken=parse_result.get('stoken')
                root=ShareFile(type=FileType.FOLDER,name='根',id=pdir_fid,children=lazy(lambda :self._quark_get_dir(pdir_fid,quark_client=quark_parse_client,movie=movie)))
                yield QuarkLinkParse(pwd_id=pwd_id,passcode=passcode,stoken=stoken,pdir_fid=pdir_fid,root=root,link=quark_link)


quark_link_parser=QuarkLinkPaser()
async def main():
    setup_logging()
    await init_db()
    result=await quark_link_parser.parse_links([PrepareParseLinks(links=[CloudShareLink(url='https://pan.quark.cn/s/a93f5bc0ef11')],scrape_quark_links=lazy(AsyncCachedIterator([CloudShareLink(url='https://pan.quark.cn/s/a93f5bc0ef11'),CloudShareLink(url='https://pan.quark.cn/s/c117cff27ccf')])),movie=Movie(douban_id='1',title_season='asd',movie_type=MovieType.TV,tmdb_infos=TMDBInfos(season_number=4)))])
    for r in result:
        async for i in r.quark_parses:
            for j in await i.root.children:
                for k in await j.children:
                    print(await k.standardized)

if __name__=='__main__':
    asyncio.run(main())