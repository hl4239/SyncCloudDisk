import asyncio
from re import search

from Services.crawler_resource.crawler import ResourceQuark, QuarkFile, SearchResult
from Services.crawler_resource.telegram.t_me_crawler import TMeCrawler
from lxml import html

from Services.episode_namer_dir.public_episode_namer import PublicEpisodeNamer
from Services.quark_share_dir_tree import QuarkShareDirTree


class TMeUCQuarkCrawler(TMeCrawler):
    def __init__(self) -> None:

        super().__init__('https://t.me/s/ucquark')

    async def parse_search(self, text:str):
        tree=html.fromstring(text)
        # XPath 查询
        links = tree.xpath(
            '//div[contains(@class, "tgme_widget_message_wrap")]'
            '//div[contains(@class, "tgme_widget_message")]'
            '//div[contains(@class, "tgme_widget_message_bubble")]'
            '//div[contains(@class, "tgme_widget_message_text")]'
            '//a[contains(@href, "quark.cn")]/@href')
        return links
    async def search(self, keyword:str,year:str):
        text= await self.search_telegram(keyword)
        links= await self.parse_search(text)
        target_link=links[-1]
        print(target_link)
        video_list=await self.parse_quark_share(target_link)
        resource_quark_list=[
            QuarkFile(file_name=i['file_name'],fid=i['fid'],share_fid_token=i['share_fid_token'])
            for i in video_list
        ]
        resource_quark_list= await self.clean_quark_file_list(resource_quark_list)

        resource_quark=ResourceQuark(title=keyword,url=target_link,file_list=resource_quark_list)
        search_result= SearchResult(keyword=keyword,result=[resource_quark])
        return search_result

    async def parse_quark_share(self,share_link:str):
        quark_dir_tree=QuarkShareDirTree.get_quark_share_tree(share_link)
        await quark_dir_tree.parse(10,refresh=True)
        video_list= quark_dir_tree.get_video_node_info()
        return video_list

    async def clean_quark_file_list(self,quark_file_list:[QuarkFile]):
        g_name_list =await PublicEpisodeNamer.generate_name([
            i.file_name
            for i in quark_file_list
        ])
        g_name_list = list({item.format_name: item for item in g_name_list}.values())

        remove_duplicate_list=  PublicEpisodeNamer.remove_duplicates([
            i.format_name
            for i in g_name_list
        ])
        g_name_list=[
            i
            for i in g_name_list if i.format_name in remove_duplicate_list
        ]

        resource_quark_maps={
            i.file_name:i
            for i in quark_file_list

        }
        for g in g_name_list:
            resource_quark_maps[g.original_name].format_name = g.format_name
        g_name_list = list({item.format_name: item for item in g_name_list}.values())

        remove_duplicate_list = PublicEpisodeNamer.remove_duplicates([
            i.format_name
            for i in g_name_list
        ])
        g_name_list = [
            i
            for i in g_name_list if i.format_name in remove_duplicate_list
        ]

        resource_quark_maps = {
            i.file_name: i
            for i in quark_file_list

        }
        for g in g_name_list:
            resource_quark_maps[g.original_name].format_name = g.format_name
        return [
            quark_file
            for quark_file in quark_file_list
            if quark_file.format_name is not None
        ]
    async def close(self):
        await self.session.close()
async def main():
    crawler=TMeUCQuarkCrawler()
    result= await crawler.search('折腰')
    print(result)
if __name__ == '__main__':
    asyncio.run(main())