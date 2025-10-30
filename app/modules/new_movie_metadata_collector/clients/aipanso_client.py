import re
from time import sleep

import aiohttp
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from lxml import etree
from typing import List

import asyncio # Add asyncio for async operations
from app.core.abc_aio_client import BaseAioClient, aio_client_manager  # Import BaseAioClient
from app.utils.tools import make_cookiejar


class AipansouClient(BaseAioClient):
    def __init__(self):
        self.ck_ml_sea = ""
        initial_cookies = {
            '_egg': '4d6cd5f1cbc2439db3cd709e330418d6e',
            'ck_ml_sea_': self.ck_ml_sea, # This will be empty initially, updated later
            '_bid': '33f7541ec56d6c1e2e87fbbd4d5124fd'
        }
        # The BaseAioClient's init method handles cookie_jar creation
        super().__init__()
        super().init(
            "aipanso",
            base_url="https://aipanso.com",
            headers={
                'pragma': 'no-cache',
                'priority': 'u=0, i',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'Referer': 'https://aipanso.com/cv/L2xgqeJjpur9cPCcop6z8EaN', # This will be updated dynamically
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Host': 'aipanso.com',
                'Connection': 'keep-alive'
            },
            # Pass the initial cookies directly, aio_client_manager will manage the cookie_jar
            cookie_jar=make_cookiejar(initial_cookies)
        )
        self.headers = aio_client_manager._configs.get("aipanso", {}).get("headers", {})



    async def _set_ck_ml_sea(self, text):
        plaintext_str = text
        key_str = "1234567812345678"
        iv_str = "1234567812345678"

        key_bytes = key_str.encode('utf-8')
        iv_bytes = iv_str.encode('utf-8')
        plaintext_bytes = plaintext_str.encode('utf-8')

        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        padded_plaintext = pad(plaintext_bytes, AES.block_size)
        ciphertext_bytes = cipher.encrypt(padded_plaintext)
        self.ck_ml_sea = binascii.hexlify(ciphertext_bytes).decode('utf-8')
        # Update the cookie_jar directly through the session
        session = await self.get_session()
        session.cookie_jar.update_cookies({'ck_ml_sea_': self.ck_ml_sea})

    def _check_response_type(self, html_content):
        pattern = r'\bstart_load\s*\(\s*\"([0-9a-fA-F]{64,})\"\s*\)\s*;?'
        match = re.search(pattern, html_content)
        return match.group(1) if match else ""

    async def _get_resource(self, target):
        url = f"https://aipanso.com/cv/{target}"
        self.headers['Referer'] = url
        # Update the headers with the new Referer

        # Use self.cookie_jar directly
        resp = await self.request("GET", url, as_type="resp", allow_redirects=False)
        return resp.headers.get('Location') if resp.status == 302 else None

    async def search(self, keyword: str,num:int):
        results = []
        url = f"https://aipanso.com/search?k={keyword}"

        # 第一次请求获取加密参数
        response_text = await self.request("GET", url, as_type="text", headers=self.headers, cookie_jar=self.cookie_jar, ssl=True)
        check = self._check_response_type(response_text)
        if check:
            self._set_ck_ml_sea(check)
            response_text = await self.request("GET", url, as_type="text", headers=self.headers, cookie_jar=self.cookie_jar, ssl=True)

        # 解析结果
        tree = etree.HTML(response_text)
        a_list = tree.xpath("//a[contains(@href, '/s/')]")
        target_list=[]
        for a in a_list:
            url = a.xpath('./@href')[0]
            target = re.search('/s/(.*)', url).group(1)
            div_title = a.xpath('.//div[@name="content-title"]')[0]
            title = div_title.xpath('string(.)').strip()
            a_allstr= re.sub(r'\s+', '', a.xpath('string(.)'))

            match1=re.search('(.*)时间:(.*)格式:',a_allstr)
            title=match1.group(1)
            time=match1.group(2)
            target_list.append({
                'title': title,
                'url': url,

                'time': time,
                'target': target,
            })

        # 按时间排序(最新的在前)
        sorted_results = sorted(target_list, key=lambda x: x['time'], reverse=True)
        # 只转存最新的一个结果

        latest_target_results = sorted_results[:num]

        for l in latest_target_results:

            result=None
            resource_url = self._get_resource(l['target'])
            if resource_url:
                # r = SearchResult(
                #     title=l['title'],
                #     url=resource_url,
                #     size="",  # 可以从页面中提取大小信息
                #     time=l['time'],
                #     source="aipansou"
                # )
                r=None
                yield r

    async def get_hot_key(self):
        """
        浏览 Aipanso 首页内容并提取热搜榜词条。
        """
        homepage_url = "https://aipanso.com"
        # 第一次请求获取加密参数
        response_text = await self.request("GET", homepage_url, as_type="text", headers=self.headers,
                                           ssl=True)
        check = self._check_response_type(response_text)
        if check:
            await self._set_ck_ml_sea(check)
            response_text = await self.request("GET", homepage_url, as_type="text", headers=self.headers,
                                               ssl=True)

        # 使用 lxml 解析 HTML
        tree = etree.HTML(response_text)

        # 使用 XPath 找到“热搜”标签下的所有链接
        # //van-tab[@title="🔥热搜"] selects the "hot search" tab content.
        # //a selects all anchor tags within that tab.
        hot_search_links = tree.xpath('//van-tab[@title="🔥热搜"]//a')

        hot_search_terms = []
        for link in hot_search_links:
            # 提取链接的文本内容，例如 " 1. 暗河传"
            text = link.text
            if text:
                # 清理字符串：去除首尾空格，并移除数字和点号
                # re.sub(r'^\s*\d+\.\s*', '', text) finds a pattern at the start (^) of the string
                # which includes optional whitespace (\s*), one or more digits (\d+), a literal dot (\.),
                # and more optional whitespace, and replaces it with an empty string.
                clean_term = re.sub(r'^\s*\d+\.\s*', '', text)
                if clean_term:
                    hot_search_terms.append(clean_term)

        return hot_search_terms
aipanso_client = AipansouClient()
async def main():

    r= await aipanso_client.get_hot_key()
    print(r)
if __name__ == '__main__':
    asyncio.run(main())