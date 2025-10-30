import asyncio
import logging


from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.movie_repository import movie_repository
from app.modules.data_standard.schemas import StandardizedResult
from app.modules.data_standard.services.regex_standardizer import regex_standardizer
from app.modules.link_parse.clients.baidu_parse_client import BaiduParseClient
from app.modules.link_parse.clients.quark_parse_client import QuarkParseClient
from app.modules.link_parse.interfaces.link_parser_interface import ILinkParser
from app.modules.link_parse.schemas import ShareFile, FileType, QuarkLinkParse, PrepareParseLinks, BaiduLinkParse
from app.utils.async_iterator import AsyncCachedIterator, AsyncMergedCachedIterator
from app.utils.lazy_load import lazy
from app.database.models import Movie, CloudType, CloudShareLink


logger = logging.getLogger(__name__)


class LinkPaser(ILinkParser):

    @classmethod
    async def _quark_get_dir(cls,p_file:ShareFile, pdir_fid: str, quark_client: QuarkParseClient, movie: Movie):

        ls_resp = await quark_client.ls_dir(pdir_fid)
        result = []
        if file_list := ls_resp.get('list'):

            for file in file_list:
                name = file.get('file_name')
                id_ = file.get('fid')
                type_ = FileType.FOLDER if file.get("file_type") == 0 else FileType.FILE
                id_token = file.get('share_fid_token')
                share_file = ShareFile(name=name, id=id_, type=type_, parent_id=pdir_fid, share_fid_token=id_token)

                result.append(share_file)
            season_number = movie.get_season_number()
            standardized_results = [
                StandardizedResult(original_name=f.name, season_number=(await p_file.standardized).season_number, is_folder=f.is_folder) for
                f in result]
            for f in result:
                f.standardized = lazy(lambda i=f.name: regex_standardizer.get_standardized_result(target_original=i,
                                                                                                  items=standardized_results))
                if f.is_folder:
                    f.children = lazy(lambda i=f.id,ii=f: cls._quark_get_dir(ii,i, quark_client, movie))

        logger.debug(f'获取pdir_fid={pdir_fid}目录,result={result}')
        return result

    @classmethod
    async def _baidu_get_dir(cls,p_file:ShareFile, pdir_path: str, baidu_client: BaiduParseClient, movie: Movie):


        ls_resp = await baidu_client.ls_dir(pdir_path)
        result = []
        if file_list := ls_resp.get('list'):
            for file in file_list:
                name = file.get('server_filename')
                id_ = str(file.get('fs_id'))
                type_ = FileType.FOLDER if file.get("isdir") == 1 else FileType.FILE
                path=file.get('path')
                share_file = ShareFile(name=name, id=id_, type=type_,
                                       path=path,

                                       )

                result.append(share_file)
            season_number = (await p_file.standardized).season_number
            standardized_results = [
                StandardizedResult(original_name=f.name, season_number=season_number, is_folder=f.is_folder) for
                f in result]
            for f in result:
                f.standardized = lazy(lambda i=f.name: regex_standardizer.get_standardized_result(target_original=i,
                                                                                                  items=standardized_results))
                if f.is_folder:
                    f.children = lazy(lambda i=f.path,k=f: cls._baidu_get_dir(k,i, baidu_client, movie))

        logger.debug(f'获取path={pdir_path}目录,result={result}')
        return result

    async def parse_quark(self, prepare_parse_links: PrepareParseLinks):

        links_quark = [link for link in prepare_parse_links.links if link.type == CloudType.QUARK]

        scrape_quark_links = await prepare_parse_links.scrape_quark_links
        movie = prepare_parse_links.movie
        async for quark_link in AsyncMergedCachedIterator([links_quark, scrape_quark_links]):
            quark_parse_client = QuarkParseClient(quark_link.url)
            parse_result = await quark_parse_client.parse_share_link()
            if parse_result.get('ok'):

                pwd_id = parse_result.get('pwd_id')
                passcode = parse_result.get('passcode')
                pdir_fid = parse_result.get('pdir_fid')
                stoken = parse_result.get('stoken')
                root = ShareFile(type=FileType.FOLDER, name='根', id=pdir_fid,standardized=lazy(StandardizedResult(season_number=movie.get_season_number(),)))

                # 再单独赋值 children，让闭包安全引用 root
                root.children = lazy(
                    lambda i=quark_parse_client, j=pdir_fid,k=root:
                    self._quark_get_dir(k, j, quark_client=i, movie=movie)
                )

                yield QuarkLinkParse(pwd_id=pwd_id, passcode=passcode, stoken=stoken, pdir_fid=pdir_fid, root=root,
                                     link=quark_link)

    async def parse_baidu(self, prepare_parse_links: PrepareParseLinks):
        links_quark = [link for link in prepare_parse_links.links if link.type == CloudType.BAIDU]

        scrape_baidu_links = await prepare_parse_links.scrape_baidu_links
        movie = prepare_parse_links.movie
        async for baidu_link in AsyncMergedCachedIterator([links_quark, scrape_baidu_links]):
            baidu_parse_client = BaiduParseClient(baidu_link.url,password=baidu_link.share_password)
            parse_result = await baidu_parse_client.parse_share_link()
            print(parse_result)
            if parse_result.get('ok'):

                uk = parse_result.get('uk')
                share_id = parse_result.get('share_id')
                bdstoken = parse_result.get('bdstoken')
                sekey = parse_result.get('sekey')
                root_files = parse_result.get('file_list')
                if not root_files:
                    continue

                root = ShareFile(type=FileType.FOLDER, name='根', id='0', path='/',
                                 standardized=lazy(StandardizedResult(season_number=movie.get_season_number(),))
                                 )

                children = []

                for i in root_files:
                    is_folder = i['isdir'] != 0
                    name = i['server_filename']
                    path = i['path']
                    fid = str(i['fs_id'])

                    # 1️⃣ 先创建 ShareFile 基础对象（不带 children/standardized）
                    child = ShareFile(
                        type=FileType.FOLDER if is_folder else FileType.FILE,
                        name=name,
                        id=fid,
                        path=path,
                    )

                    # 2️⃣ 再绑定 children（避免闭包引用错误）
                    if is_folder:
                        child.children = lazy(
                            lambda i1=path, i2=baidu_parse_client,i3=child:
                            self._baidu_get_dir(i3, i1, i2, movie=movie)
                        )
                    else:
                        child.children = lazy(None)

                    # 3️⃣ 再绑定 standardized（延迟标准化）
                    child.standardized = lazy(
                        lambda i1=name, i2=i: regex_standardizer.get_standardized_result(
                            target_original=i1,
                            items=[
                                StandardizedResult(
                                    original_name=i1,
                                    season_number=movie.get_season_number(),
                                    is_folder=is_folder
                                )
                            ]
                        )
                    )

                    children.append(child)

                # 4️⃣ 最后一次性挂载到 root.children
                root.children = lazy(children)

                yield BaiduLinkParse(uk=str(uk), share_id=str(share_id), bdstoken=str(bdstoken), sekey=str(sekey), root=root,
                                     link=baidu_link)


link_parser = LinkPaser()


async def main():
    setup_logging()
    await init_db()
    movie = await movie_repository.find_by_douban_id('36563149')

    result = await link_parser.parse_links([PrepareParseLinks(
        links=[CloudShareLink(url='https://pan.baidu.com/s/1n1DJgJ0R_hEvRgthLlbj0Q?pwd=8u62')],
        scrape_quark_links=lazy(lambda: AsyncCachedIterator([])),
        scrape_baidu_links=lazy(lambda: AsyncCachedIterator([])),
        movie=movie)])
    for r in result:
        async for i in r.baidu_parses:
            print(i.root)
            for j in await i.root.children:
                print(j.children)
                for k in await j.children:
                    print((await k.standardized))

    # result=await link_parser.parse_links([PrepareParseLinks(links=[CloudShareLink(url='https://pan.quark.cn/s/f420b5c05815')],scrape_quark_links=lazy(lambda : AsyncCachedIterator([])),movie=movie)])
    #
    # for r in result:
    #     async for i in r.quark_parses:
    #         for j in await i.root.children:
    #             for k in await j.children:
    #                 if k.is_folder:
    #                     for l in await k.children:
    #                         print(await k.standardized)


if __name__ == '__main__':
    asyncio.run(main())
