import asyncio

import aiohttp

from lxml import html

from Services.crawler_torrent.crawler import SearchResult, Resource, ResourceType


class PanDianCrawler:
    def __init__(self):
        headers={}
        self.session = aiohttp.ClientSession(headers=headers)
        self.base_url='https://www.dyttgou.com'
    async def _search(self,title):
        url=self.base_url+'/e/search/index.php'
        payload={
            'keyboard':title,
            'show':'title',
            'tempid':1,
            'tbname':'video',
        }
        # 清除所有 Cookie
        self.session.cookie_jar.clear()
        async with self.session.post(url,data=payload) as resp:
            text = await resp.text()
            return text

    async def _parse_search_text(self,text):
        # 解析 HTML
        tree = html.fromstring(text)
        # 使用 XPath 定位 href

        all_hrefs = tree.xpath('//a[@class="entry-thumb lazyload"]/@href')
        try:
            # 默认处理第一个
            href=all_hrefs[0]
            return href
        except Exception as e:
            raise Exception(f'处理盘点影视搜索界面发生错误{str(e)}')

    async def _get_detail(self,href:str):
        url=self.base_url+href
        async with self.session.get(url) as resp:
            text = await resp.text()
            return text

    async def _parse_detail_text(self, text) -> list[Resource]:
        tree = html.fromstring(text)
        resources = []

        # 遍历所有匹配的磁力链接元素
        for element in tree.xpath('//div[@id="zdownload"]/a[span="磁力下载"]'):
            # 提取磁力链接
            magnet_link = element.xpath('./@href')[0]  # 当前<a>的href属性

            # 提取标题（从<a>的文本内容中排除<span>部分）
            title = "".join(
                text.strip() for text in element.xpath('./text()')
                if text.strip() and text.strip() != "磁力下载"
            ).strip()

            # 创建Resource对象并添加到列表
            resources.append(
                Resource(url=magnet_link, title=title if title else "未知标题",type=ResourceType.MAGNET)
            )

        if not resources:
            raise Exception(f"处理盘点影视资源详情页面发生错误，未找到任何磁力链接")

        return resources

    async def search(self,title,rety:int=3):
        for i in range(rety):
            search_text= await self._search(title)

            try:
                href= await self._parse_search_text(search_text)
            except Exception as e:
                if i==rety-1:
                    raise Exception(f'搜索{title}失败   {str(e)}')
                print(f'{e} 进行第{i+1}此重试')
                continue
            text= await self._get_detail(href)
            for j in range(rety):
                try:
                    resource_list= await self._parse_detail_text(text)

                    search_result=SearchResult(keyword=title)
                    search_result.result=resource_list

                    return search_result
                except Exception as e:
                    if j == rety-1:
                        raise Exception(f'已搜索到{title}资源，但链接获取失败{str(e)}')
                    else:
                        print(f'{e} 进行第{j + 1}此重试')

            break




async def main():
    pandianCrawler= PanDianCrawler()
    try:
        result=await pandianCrawler.search('折腰')
    except Exception as e:
        print(e)
if __name__ == '__main__':
    asyncio.run(main())