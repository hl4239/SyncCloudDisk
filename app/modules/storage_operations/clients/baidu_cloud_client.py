import asyncio
import json
import logging
import time
from typing import Optional, Dict, List
from pathlib import Path

import aiohttp

from app.core.abc_aio_client import BaseAioClient
from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import PanCloud
from app.utils.cache import async_ttl_cache
from app.utils.tools import make_cookiejar

logger = logging.getLogger(__name__)



class BaiduCloudClient(BaseAioClient):
    def __init__(self, pancloud_name: str, cookies_str: str):
        self.BASE_URL = 'https://pan.baidu.com'
        self.PCS_URL = 'https://pcs.baidu.com'
        self.headers = {}
        self.cookies_str = cookies_str
        self.pancloud_name = pancloud_name
        self._bdstoken = None
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()
        super().__init__()

        # Parse cookies to extract BDUSS, STOKEN
        cookies_dict = {}
        for item in cookies_str.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies_dict[key] = value

        self.bduss = cookies_dict.get('BDUSS', '')
        self.stoken = cookies_dict.get('STOKEN', '')

        super().init(
            name=self.pancloud_name,
            base_url=self.BASE_URL,
            headers={
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Pragma': 'no-cache',
                'Referer': 'https://pan.baidu.com/disk/main',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest',
                'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'Host': 'pan.baidu.com',
            },
            cookie_jar=make_cookiejar(cookies_str,quote_cookie=False)
        )


    async def request(self, method: str, url: str, *, params=None, data=None, json=None, headers=None,**kwargs):
        # 合并默认 params 和调用时传入的 params
        # return await session.request(method, url, params=params, data=data, json=json, headers=headers)
        proxy = "http://127.0.0.1:8866"

        # 限速逻辑
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            min_interval = 1.0  # 最少间隔 1 秒

            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)

            self._last_request_time = time.monotonic()

            # 真正发请求
            return await super().request(
                method, url,
                params=params, data=data, json=json, headers=headers,
                as_type='resp', **kwargs
            )
    async def _get_bdstoken(self) -> str:
        """Get bdstoken from pan.baidu.com"""
        if self._bdstoken:
            return self._bdstoken

        url = f"{self.BASE_URL}/disk/home"
        async with await self.request(method="GET", url=url) as resp:
            import re
            text = await resp.text()
            match = re.search(r'bdstoken[\'":\s]+([0-9a-f]{32})', text)
            if match:
                self._bdstoken = match.group(1)
                return self._bdstoken
        return ""

    async def connect(self) -> bool:
        """Test connection by listing root directory"""
        url = f"{self.BASE_URL}/api/list"
        params = {
            "num": "1",
            "web": "1",
            "clienttype":0,
            "app_id":250528,
            "dp-logid":'13560200717733650050',
            "desc":1,
            "order":"time",
            "page":1,
        }

        async with await self.request(method="GET", url=url, params=params) as resp:
            try:
                data = await resp.json()
                if data.get("errno") == 0:
                    logger.info(f'已成功连接百度网盘({self.pancloud_name})')
                    return True
                else:

                    logger.error(f'|{self.pancloud_name}|连接失败: errno={data}')
                    return False
            except Exception as e:
                logger.error(f'连接失败: {e}')
                return False

    async def list(self, remotepath: str = "/", page: int = 1, num: int = 100) -> List[Dict]:
        """List directory contents"""
        url = f"{self.BASE_URL}/api/list"
        params = {
            "dir": remotepath,
            "page": page,
            "num": num,
            "order": "name",
            "desc": "0",
            "web": "1",
        }

        async with await self.request(method="GET", url=url, params=params) as resp:
            data = await resp.json()
            if data.get("errno") == 0:
                return data.get("list", [])
            else:
                raise RuntimeError(f"列出目录失败: {data.get('errmsg', '未知错误')}")

    async def mkdir(self, remotepath: str) -> bool:
        """Create directory"""
        url = f"{self.BASE_URL}/api/create"
        params = {
            "a": "commit",
                'bdstoken':await self._get_bdstoken(),
            "web": "1",
            'clienttype':0,
            'app_id':250528,
            'dp-logid':'13560200717733650084',
        }
        data={
             "path": remotepath,
            "isdir": "1",
            "block_list": "[]",
        }

        async with await self.request(method="POST", url=url, params=params,data=data) as resp:
            data = await resp.json()
            if data.get("errno") == 0:
                return True
            else:
                raise RuntimeError(f"创建目录失败: {data}")

    async def move(self, file_list: List[Dict[str, str]]) -> bool:
        """Move files/directories"""
        url = f"{self.BASE_URL}/api/filemanager"
        params = {"opera": "move"}
        payload = {
            "filelist": json.dumps([{"path": item["path"], "dest": item["dest"], "newname": item.get("newname", "")}
                                    for item in file_list])
        }

        async with await self.request(method="POST", url=url, params=params, data=payload) as resp:
            data = await resp.json()
            print(data)
            if data.get("errno") == 0:

                return True

            else:
                raise RuntimeError(f"移动文件失败: {data.get('errmsg', '未知错误')}")

    async def rename(self, remotepath: str, newname: str) -> bool:
        """Rename file/directory"""
        url = f"{self.BASE_URL}/api/filemanager"
        params = {"opera": "rename"}
        payload = {
            "filelist": json.dumps([{"path": remotepath, "newname": newname}])
        }

        async with await self.request(method="POST", url=url, params=params, data=payload) as resp:
            data = await resp.json()
            if data.get("errno") == 0:
                return True
            else:
                logger.warning(f"重命名失败: {data.get('errmsg', '未知错误')}")
                return False

    async def delete(self, remotepaths: List[str]) -> bool:
        """Delete files/directories"""
        url = f"{self.BASE_URL}/api/filemanager"
        params = {
            "opera": "delete",
            "bdstoken":await self._get_bdstoken(),


        }
        payload = {
            "filelist": json.dumps(remotepaths)
        }

        async with await self.request(method="POST", url=url, params=params, data=payload) as resp:
            data = await resp.json()
            if data.get("errno") == 0:
                return True
            else:
                raise RuntimeError(f"删除失败: {data}")

    async def share(self, remotepaths: List[str], password: str = "8u62", period: int = 0) -> Dict:
        """Create share link"""
        bdstoken = await self._get_bdstoken()
        url = f"{self.BASE_URL}/share/set"

        # Get fs_ids first
        meta_list = []
        for path in remotepaths:
            p_str= str(Path(path).parent.as_posix())
            files = await self.list(p_str)
            for f in files:
                if f["path"] == path:
                    meta_list.append(f)
                    break

        fs_ids = [f["fs_id"] for f in meta_list]

        params = {
            "channel": "chunlei",
            "clienttype": "0",
            "web": "1",
            "bdstoken": bdstoken
        }

        payload = {
            "fid_list": json.dumps(fs_ids),
            "schannel": "4" if password else "0",
            "channel_list": "[]",
            "period": str(period),
            "public":"0",
            "is_knowledge":"0",
            "pwd":password,

        }

        if password:
            payload["pwd"] = password

        async with await self.request(method="POST", url=url, params=params, data=payload) as resp:
            data = await resp.json()
            if data.get("errno") == 0:
                return {
                    "share_id": data.get("shareid"),
                    "link": data.get("link"),
                    "shorturl": data.get("shorturl")
                }
            else:
                raise RuntimeError(f"分享失败: {data}")

    async def download_link(self, remotepath: str) -> str:
        """Get download link"""
        url = f"{self.PCS_URL}/rest/2.0/pcs/file"
        params = {
            "method": "locatedownload",
            "app_id": "250528",
            "path": remotepath
        }

        async with await self.request(method="GET", url=url, params=params) as resp:
            data = await resp.json()
            if "urls" in data and len(data["urls"]) > 0:
                return data["urls"][0]["url"]
            else:
                raise RuntimeError(f"获取下载链接失败")

    async def save_from_share(
            self,
            remotedir: str,
            fs_ids: List[int],
            uk: int,
            share_id: int,
            shared_url: str,
            sekey:str
    ) -> bool:
        """转存已解析的分享文件

        Args:
            remotedir: 目标保存目录
            fs_ids: 文件ID列表
            uk: 分享者用户ID
            share_id: 分享ID
            bdstoken: 安全令牌
            shared_url: 分享链接(用于Referer)
        """
        logger.debug(f'开始百度转存：{remotedir} {fs_ids} {uk} {share_id} {shared_url} {sekey}')
        url = "https://pan.baidu.com/share/transfer"
        params = {
            "shareid": str(share_id),
            "from": str(uk),
            "bdstoken":await self._get_bdstoken(),
            "channel": "chunlei",
            "clienttype": "0",
            "web": "1",
            "sekey":sekey
        }
        data = {
            "fsidlist": json.dumps(fs_ids),
            "path": remotedir,
        }
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://pan.baidu.com",
            "Referer": shared_url,
        }

        async with await self.request("POST", url, params=params, data=data, headers=headers) as resp:
            result = await resp.json()
            if result.get("errno") == 0:
                return True
            raise Exception(f'百度转存失败|{remotedir} {shared_url}：{result}')



@async_ttl_cache(key_fields=['name'])
async def get_baidu_pcs_client(pancloud: PanCloud):
    logger.debug(f'开始获取{pancloud.name}的百度网盘client')
    name = pancloud.name
    cookies = pancloud.cookie
    res=BaiduCloudClient(name, cookies)

    if  await res.connect():

        return res
    return None

async def main():
    await init_db()
    setup_logging()
    p = await PanCloud.find_one(PanCloud.name == '4295baidu')
    client = await get_baidu_pcs_client(p)
    res = await client.connect()
    res=await client.list('/资源分享/asd')
    # res=await client.mkdir(remotepath='/资源分享/asd')
    # res=await client.rename('/资源分享/asd','asd111')
    # res=await client.delete(remotepaths=['/资源分享/asd111'])
    # res=await client.share(remotepaths=['/资源分享'])
    # print(res)
    # # 示例：解析百度网盘分享链接
    # share_url = "https://pan.baidu.com/s/1rEtwxw-zUZ97cpOeV1ldkQ"
    # password = "uuq9"  # 如果有密码
    #
    # client_parse = BaiduParseClient(share_url, password)
    #
    # # 解析分享链接
    # result = await client_parse.parse_share_link()
    # print("解析结果:", result)
    # for_save_files=[]
    #
    #
    # if result["ok"]:
    #     # 列出根目录文件
    #     file_list = result["file_list"]
    #     print(f"文件数量: {len(file_list)}")
    #
    #     # 如果有子目录，可以继续列出
    #     for item in file_list:
    #         if item.get("isdir") == 1:
    #             ls_result = await client_parse.ls_dir(item["path"])
    #             print(f"子目录 {item['path']} 内容:", ls_result)
    #             for i in ls_result['list']:
    #                 for_save_files.append(i['fs_id'])

    # res=  await client.save_from_share(
    #     remotedir='/资源分享/asd',
    #     fs_ids=for_save_files,
    #     uk=client_parse.uk,
    #     share_id=client_parse.share_id,
    #     shared_url=share_url,
    #     sekey=client_parse.sekey,
    # )
    print(res)


if __name__ == "__main__":
    asyncio.run(main())