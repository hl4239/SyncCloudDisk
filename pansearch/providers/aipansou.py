import re
from time import sleep
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from lxml import etree
from typing import List
from ..interface import SearchResult, BaseProvider

class AipansouProvider(BaseProvider):
    def __init__(self):
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
        self.cookies={
            '_egg': '4d6cd5f1cbc2439db3cd709e330418d6e',
            'ck_ml_sea_': self.ck_ml_sea,
            '_bid' : '33f7541ec56d6c1e2e87fbbd4d5124fd'
        }

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
        self.cookies['ck_ml_sea_']= self.ck_ml_sea = binascii.hexlify(ciphertext_bytes).decode('utf-8')

    def _check_response_type(self, html_content):
        pattern = r'\bstart_load\s*\(\s*\"([0-9a-fA-F]{64,})\"\s*\)\s*;?'
        match = re.search(pattern, html_content)
        return match.group(1) if match else ""

    def _get_resource(self, target):
        url = f"https://aipanso.com/cv/{target}"
        self.headers['Referer'] = url
        cookies = {
            '_egg': '4d6cd5f1cbc2439db3cd709e330418d6e',
            'ck_ml_sea_': self.ck_ml_sea,
        }
        response = requests.get(url, headers=self.headers, cookies=self.cookies,
                              verify=True, allow_redirects=False)
        return response.headers['Location'] if response.status_code == 302 else None

    def search(self, keyword: str,num:int):
        results = []
        url = f"https://aipanso.com/search?k={keyword}"

        # 第一次请求获取加密参数
        response = requests.get(url, headers=self.headers, cookies=self.cookies, verify=True)
        check = self._check_response_type(response.text)
        if check:
            self._set_ck_ml_sea(check)

            response = requests.get(url, headers=self.headers, cookies=self.cookies, verify=True)

        # 解析结果
        tree = etree.HTML(response.text)
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
                r = SearchResult(
                    title=l['title'],
                    url=resource_url,
                    size="",  # 可以从页面中提取大小信息
                    time=l['time'],
                    source="aipansou"
                )
                yield r