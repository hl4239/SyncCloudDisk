import asyncio
import re
import types
from time import sleep
import aiohttp
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from lxml import etree
from typing import List

from app.domain.models.share_link_crawler_results import ShareLinkCrawlerResults
from app.infrastructure.config import CloudAPIType
from app.infrastructure.crawlers.share_link_crawler import ShareLinkCrawler


class AiPanSoCrawler(ShareLinkCrawler):
    def __init__(self):

        super().__init__()
        self.ck_ml_sea = ""
        self.headers = {
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'Referer': 'https://aipanso.com/cv/L2xgqeJjpur9cPCcop6z8EaN',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Host': 'aipanso.com',
            'Connection': 'keep-alive'
        }
        self.cookies = {
            '_egg': '4d6cd5f1cbc2439db3cd709e330418d6e',
            'ck_ml_sea_': self.ck_ml_sea,
            '_bid': '33f7541ec56d6c1e2e87fbbd4d5124fd'
        }
        self.session = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def init(self):
        """创建aiohttp会话"""
        if self.session is None:
            connector = aiohttp.TCPConnector(ssl=True)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            )

    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    def _set_ck_ml_sea(self, text):
        plaintext_str = text
        key_str = "1234567812345678"
        iv_str = "1234567812345678"

        key_bytes = key_str.encode('utf-8')
        iv_bytes = iv_str.encode('utf-8')
        plaintext_bytes = plaintext_str.encode('utf-8')

        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        padded_plaintext = pad(plaintext_bytes, AES.block_size)
        ciphertext_bytes = cipher.encrypt(padded_plaintext)
        self.cookies['ck_ml_sea_'] = self.ck_ml_sea = binascii.hexlify(ciphertext_bytes).decode('utf-8')

    def _check_response_type(self, html_content):
        pattern = r'\bstart_load\s*\(\s*\"([0-9a-fA-F]{64,})\"\s*\)\s*;?'
        match = re.search(pattern, html_content)
        return match.group(1) if match else ""

    async def _get_resource(self, target):
        if not self.session:
            await self._create_session()

        url = f"https://aipanso.com/cv/{target}"
        headers = self.headers.copy()
        headers['Referer'] = url

        cookies = {
            '_egg': '4d6cd5f1cbc2439db3cd709e330418d6e',
            'ck_ml_sea_': self.ck_ml_sea,
        }

        try:
            async with self.session.get(
                    url,
                    headers=headers,
                    cookies=cookies,
                    allow_redirects=False
            ) as response:
                if response.status == 302:
                    return response.headers.get('Location')
                return None
        except aiohttp.ClientError as e:
            print(f"Error in _get_resource: {e}")
            return None

    async def _search(self, keyword: str, num: int):
        print('开始搜索')
        if not self.session:
            await self._create_session()

        results = []
        url = f"https://aipanso.com/search?k={keyword}"

        try:
            # 第一次请求获取加密参数
            async with self.session.get(
                    url,
                    headers=self.headers,
                    cookies=self.cookies
            ) as response:
                response_text = await response.text()

            check = self._check_response_type(response_text)
            if check:
                self._set_ck_ml_sea(check)

                # 第二次请求
                async with self.session.get(
                        url,
                        headers=self.headers,
                        cookies=self.cookies
                ) as response:
                    response_text = await response.text()

            # 解析结果
            tree = etree.HTML(response_text)
            a_list = tree.xpath("//a[contains(@href, '/s/')]")
            target_list = []

            for a in a_list:
                url_path = a.xpath('./@href')[0]
                target = re.search('/s/(.*)', url_path).group(1)
                div_title = a.xpath('.//div[@name="content-title"]')[0]
                title = div_title.xpath('string(.)').strip()
                a_allstr = re.sub(r'\s+', '', a.xpath('string(.)'))

                match1 = re.search('(.*)时间:(.*)格式:', a_allstr)
                if match1:
                    title = match1.group(1)
                    time = match1.group(2)
                    target_list.append({
                        'title': title,
                        'url': url_path,
                        'time': time,
                        'target': target,
                    })

            # 按时间排序(最新的在前)
            sorted_results = sorted(target_list, key=lambda x: x['time'], reverse=True)


            latest_target_results = sorted_results[:num]

            for l in latest_target_results:
                resource_url = await self._get_resource(l['target'])
                yield resource_url

        except aiohttp.ClientError as e:
            print(f"Error in search: {e}")
        except Exception as e:
            print(f"Unexpected error in search: {e}")

    async def search(self, keyword: str, num: int,cloud_type:CloudAPIType):
        results = self._search(keyword=keyword, num=num)  # 这是个 async generator
        return ShareLinkCrawlerResults(title=keyword, share_links=results)



