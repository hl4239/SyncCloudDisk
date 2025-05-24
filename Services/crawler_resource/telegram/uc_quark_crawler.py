import asyncio
from re import search

from Services.crawler_resource.crawler import ResourceQuark, QuarkFile, SearchResult
from Services.crawler_resource.quark_share_crawler import QuarkShareCrawler
from Services.crawler_resource.telegram.t_me_crawler import TMeCrawler
from lxml import html

from Services.episode_namer_dir.public_episode_namer import PublicEpisodeNamer
from Services.quark_share_dir_tree import QuarkShareDirTree


class TMeUCQuarkCrawler(TMeCrawler):
    def __init__(self,quark_share_crawler:QuarkShareCrawler) -> None:
        self.quark_share_crawler = quark_share_crawler
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
        result= await self.quark_share_crawler.search(share_link=target_link,title=keyword)
        return result


    async def close(self):
        await self.session.close()
async def main():
    quark_crawler=QuarkShareCrawler()
    crawler=TMeUCQuarkCrawler(quark_crawler)
    result= await crawler.search('折腰','1233')
    print(result)
if __name__ == '__main__':
    asyncio.run(main())