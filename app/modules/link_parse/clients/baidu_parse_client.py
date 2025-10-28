import asyncio
import re
import json
import logging
from typing import Optional, Tuple, List, Dict, Any
from collections import deque
from urllib.parse import unquote

import aiohttp
from aiohttp import CookieJar

from app.core.abc_aio_client import BaseAioClient
from app.core.logging_config import setup_logging
from app.utils.tools import make_cookiejar

logger = logging.getLogger(__name__)


class BaiduParseClient(BaseAioClient):
    """
    百度网盘分享链接解析器（基于 BaseAioClient）。
    用法：
        client = BaiduParseClient(share_url, password)
        await client.parse_share_link()  # 验证密码并获取分享信息
        data = await client.ls_dir(shared_path)
        await client.close()
    """

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    BASE_URL = "https://pan.baidu.com"
    CONTEXT_NAME = 'baidu_parse_client'

    def __init__(self, share_url: str, password: Optional[str] = None):
        """
        :param share_url: 要解析的分享链接
        :param password: 分享密码（如果有）
        """
        super().__init__()

        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json, text/plain, */*",

        }
        super().init(
            name=self.CONTEXT_NAME,
            base_url=self.BASE_URL,
            headers=headers,
            cookie_jar=make_cookiejar(
                quote_cookie=False,
                cookies_str='csrfToken=hyD5XmZUg4Q0c7Yeyc6zZC7G; BAIDUID=1CCB858404BCE85500057BDEC430F41C:FG=1; BAIDUID_BFESS=1CCB858404BCE85500057BDEC430F41C:FG=1; Hm_lvt_7a3960b6f067eb0085b7f96ff5e660b0=1760291830; Hm_lpvt_7a3960b6f067eb0085b7f96ff5e660b0=1760291830; HMACCOUNT=C9C124A6247C88D1; ndut_fmt=9C18B39FBE76F9B799A2AEF1A20B25D3FB70C52B5691213DF2BE3362C290F7F4; ab_sr=1.0.1_MjI0ZjJjNDNkN2E4ZmRjNzZlYzAyODcxMjMyODJmYjBmZjc4MGZmMDQ0ZjkwZjNjZGRjZWI5ZWM4MDIwZjY0YjU3MmI2OTY4ZjZjODk3N2RhOGIwNTBjN2U5ZWVjZTY1ZDUxY2JhYWQxYzM2NzJlMTFmMjNkODk2N2VkZDc3M2Y4YTdhN2JiMjBhNzZjYzFmYjgyMDhmYTIzMGU0MTc1OA==; PANWEB=1; BDCLND=930pvqG7Ge2mGHX98ovuZNV0jEgVSoTtwWbi7ImzqN4%3D'),
        )

        # 解析/请求状态字段
        self.share_url: str = self._unify_shared_url(share_url)
        self.password: Optional[str] = password
        self.uk: Optional[int] = None
        self.share_id: Optional[int] = None
        self.sekey: Optional[str] = None
        self.bdstoken: Optional[str] = None
        self.fs_id_list: List[int] = []
    async def request(self, method: str, url: str, *, params=None, data=None, json=None, headers=None,**kwargs):
        # 合并默认 params 和调用时传入的 params
        # return await session.request(method, url, params=params, data=data, json=json, headers=headers)
        proxy = "http://127.0.0.1:8866"

        return await super().request(method, url, params=params, data=data, json=json, headers=headers,as_type='resp', **kwargs)
    def _unify_shared_url(self, url: str) -> Optional[str]:
        """统一分享链接格式"""
        # 标准格式: pan.baidu.com/s/xxx
        match = re.search(r"pan\.baidu\.com/s/(.+?)(\?|$)", url)
        if match:
            return f"https://pan.baidu.com/s/{match.group(1)}"

            # surl 格式: baidu.com...?surl=xxx
        match = re.search(r"baidu\.com.+?\?surl=(.+?)(\?|$)", url)
        if match:
            return f"https://pan.baidu.com/s/1{match.group(1)}"
        logger.warning(f"无效的分享链接格式: {url}")
        return None

    def _shared_init_url(self) -> str:
        """获取分享初始化 URL"""
        from urllib.parse import urlparse
        u = urlparse(self.share_url)
        surl = u.path.split("/s/1")[-1] if "/s/1" in u.path else u.path.split("/s/")[-1]
        return f"https://pan.baidu.com/share/init?surl={surl}"

    async def _access_shared(self) -> Tuple[bool, Optional[str]]:
        """
        验证分享密码
        返回 (ok, errmsg)
        """
        if not self.password:
            return True, None

        url = "https://pan.baidu.com/share/verify"
        init_url = self._shared_init_url()

        params = {
            "surl": init_url.split("surl=")[-1],
            "t": str(int(asyncio.get_event_loop().time() * 1000)),
            "channel": "chunlei",
            "web": "1",
            "bdstoken": "null",
            "clienttype": "0",
        }

        data = {
            "pwd": self.password,
            "vcode": "",
            "vcode_str": "",
        }

        headers = {
            "Referer": init_url,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            async with await self.request(
                    method="POST",
                    url=url,
                    params=params,
                    data=data,
                    headers=headers
            ) as resp:
                result = await resp.json()



                if result.get("errno") == 0:
                    # 提取 sekey
                    session=await self.get_session()
                    cookies_dict = {cookie.key: cookie.value for cookie in session.cookie_jar}
                    if not self.sekey:  # 如果之前没有获取到

                        self.sekey = unquote( cookies_dict.get("BDCLND"))
                    return True, None
                else:
                    return False, result.get("errmsg", "密码验证失败")

        except Exception as e:
            logger.exception("验证密码异常: %s", e)
            return False, f"异常: {e}"

    async def parse_share_link(self) -> Dict[str, Any]:
        """
        解析分享链接并获取分享信息
        返回结构:
        {
            "ok": bool,
            "uk": int|None,
            "share_id": int|None,
            "bdstoken": str|None,
            "file_list": [...],
            "error": str|None
        }
        """
        if not self.share_url:
            return {
                "ok": False,
            }
        result: Dict[str, Any] = {"ok": False, "error": None}

        # 如果有密码，先验证
        if self.password:
            ok, err = await self._access_shared()
            if not ok:
                result["error"] = err or "密码验证失败"
                logger.warning(f'{self.share_url} | {self.password} 密码验证失败')
                return result

                # 获取分享页面信息
        try:
            async with await self.request(method="GET", url=self.share_url) as resp:
                html = await resp.text()
                # 提取 sekey
                session = await self.get_session()
                cookies_dict = {cookie.key: cookie.value for cookie in session.cookie_jar}
                if not self.sekey:  # 如果之前没有获取到
                    self.sekey = unquote( cookies_dict.get("BDCLND"))

                    # 从 HTML 中提取分享数据
                match = re.search(r"(?:yunData\.setData|locals\.mset)\((.+?)\);", html)
                if not match:
                    result["error"] = "无法从分享页面提取数据"
                    return result

                shared_data = json.loads(match.group(1))

                # 提取关键信息
                self.uk = shared_data.get("share_uk") or shared_data.get("uk")
                if self.uk:
                    self.uk = int(self.uk)
                self.share_id = shared_data.get("shareid")
                self.bdstoken = shared_data.get("bdstoken")

                if not self.uk or not self.share_id or self.bdstoken is None:
                    result["error"] = "缺少必要的分享信息 (uk/share_id/bdstoken)"
                    return result

                    # 获取文件列表
                file_list_data = shared_data.get("file_list")
                if not file_list_data:
                    file_list = []
                elif isinstance(file_list_data, list):
                    file_list = file_list_data
                elif isinstance(file_list_data.get("list"), list):
                    file_list = file_list_data["list"]
                else:
                    result["error"] = "无法解析文件列表"
                    return result

                result.update({
                    "ok": True,
                    "uk": self.uk,
                    "share_id": self.share_id,
                    "bdstoken": self.bdstoken,
                    "sekey": self.sekey,
                    "file_list": file_list,
                    "error": None,
                })
                return result

        except Exception as e:
            logger.exception("解析分享链接异常: %s", e)
            result["error"] = f"异常: {e}"
            return result

    async def ls_dir(self, sharedpath: str, page: int = 1, size: int = 1000) -> Dict[str, Any]:
        """
        列出分享目录下的文件
        :param sharedpath: 分享目录路径
        :param page: 页码（从 1 开始）
        :param size: 每页数量（最大 100）
        :return: 如果成功返回 {"list": [...]}，失败返回 {"error": "..."}
        """
        if not self.uk or not self.share_id:
            return {"error": "未解析分享链接，请先调用 parse_share_link()"}

        url = f"{self.BASE_URL}/share/list"
        params = {
            "channel": "chunlei",
            "clienttype": "0",
            "web": "1",
            "page": str(page),
            "num": str(size),
            "dir": sharedpath,
            "t": str(asyncio.get_event_loop().time()),
            "uk": str(self.uk),
            "shareid": str(self.share_id),
            "desc": "1",
            "order": "other",
            "bdstoken": "null",
            "showempty": "0",
        }

        try:
            async with await self.request(method="GET", url=url, params=params) as resp:
                data = await resp.json()

                if data.get("errno") == 0:
                    return {"list": data.get("list", [])}
                else:
                    return {"error": data.get("errmsg", "列出目录失败")}

        except Exception as e:
            logger.exception("ls_dir 异常: %s", e)
            return {"error": f"异常: {e}"}

    async def list_all_files(self) -> List[Dict[str, Any]]:
        """
        递归列出分享中的所有文件
        返回所有文件的列表
        """
        parse_result = await self.parse_share_link()
        if not parse_result["ok"]:
            return []

        all_files: List[Dict[str, Any]] = []
        queue = deque(parse_result["file_list"])

        while queue:
            item = queue.popleft()
            all_files.append(item)

            # 如果是目录，递归获取子文件
            if item.get("isdir") == 1:
                page = 1
                while True:
                    result = await self.ls_dir(item["path"], page=page, size=100)
                    if result.get("error"):
                        break

                    sub_files = result.get("list", [])
                    if not sub_files:
                        break

                    queue.extend(sub_files)
                    all_files.extend(sub_files)

                    if len(sub_files) < 100:
                        break
                    page += 1

        return all_files


async def main():
    setup_logging()

    # 示例：解析百度网盘分享链接
    share_url = "https://pan.baidu.com/s/1k7nAEQ165QP3EXDCOc9rRw"
    password = "1xbg"  # 如果有密码

    client = BaiduParseClient(share_url, password)

    # 解析分享链接
    result = await client.parse_share_link()

    if result["ok"]:
        print('111')
        # 列出根目录文件
        file_list = result["file_list"]

        # 如果有子目录，可以继续列出
        for item in file_list:
            if item.get("isdir") == 1:
                ls_result = await client.ls_dir(item["path"])
    print(client.sekey)
    await client.close()


if __name__ == '__main__':
    asyncio.run(main())