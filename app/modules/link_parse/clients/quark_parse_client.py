# app/clients/quark_parse_client.py
import asyncio
import re
import urllib.parse
import logging
from typing import Optional, Tuple, List, Dict, Any

import aiohttp

from app.core.abc_aio_client import BaseAioClient
from app.core.logging_config import setup_logging

logger = logging.getLogger(__name__)


class QuarkParseClient(BaseAioClient):
    """
    Quark 云盘分享链接解析器（基于 BaseAioClient）。
    用法：
        client = QuarkParseClient()
        await client.parse_share_link()  # 解析并获取 stoken
        data = await client.ls_dir(pdir_fid)
        await client.close()
    """

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "quark-cloud-drive/3.14.2 Chrome/112.0.5615.165 Electron/24.1.3.8 "
        "Safari/537.36 Channel/pckk_other_ch"
    )
    BASE_URL = "https://drive-pc.quark.cn"
    CONTEXT_NAME='quark_parse_client'
    def __init__(self, share_link: str):
        """
        :param share_link: 要解析的分享链接
        :param context_name: 在 AioClientManager 中注册的上下文名
        """
        super().__init__()
        # 注册 context（仅注册，不创建 session）
        headers = {
            "User-Agent": self.USER_AGENT,
            "Referer": self.BASE_URL,
        }
        super().init(
            name=self.CONTEXT_NAME,
            base_url=self.BASE_URL,
            headers=headers,
        )

        # 解析/请求状态字段
        self.share_link: str = share_link
        self.pwd_id: Optional[str] = None
        self.passcode: str = ""
        self.pdir_fid: Optional[str] = None
        self.paths: List[Dict[str, str]] = []
        self.stoken: Optional[str] = None

    # ------------------ 链接解析 ------------------
    def _extract_url(self, url: str) -> Tuple[Optional[str], str, Optional[str], List[Dict[str, str]]]:
        """
        从分享链接中提取 pwd_id、passcode、目录 fid 以及路径列表。
        返回 (pwd_id, passcode, pdir_fid, paths)
        paths 格式: [{"fid": "...", "name": "..."}]
        """
        # pwd_id: /s/<pwd_id>
        match_id = re.search(r"/s/([A-Za-z0-9_-]+)", url)
        pwd_id = match_id.group(1) if match_id else None

        # passcode: ?pwd=xxx 或 &pwd=xxx
        match_pwd = re.search(r"[?&]pwd=([^&]+)", url)
        passcode = match_pwd.group(1) if match_pwd else ""

        # path segments: look for 32 长度的 fid（原实现用 \w{32}，这里放宽为 32 chars hex-like）
        paths: List[Dict[str, str]] = []
        # 支持形如 /<fid>-<name> 或 /<fid>
        matches = re.findall(r"/([A-Za-z0-9]{32})(?:-([^/]+))?", url)
        for fid, raw_name in matches:
            name = urllib.parse.unquote(raw_name) if raw_name else ""
            paths.append({"fid": fid, "name": name})

        pdir_fid = paths[-1]["fid"] if paths else '0'
        return pwd_id, passcode, pdir_fid, paths

    # ------------------ 与 Quark 接口交互 ------------------
    async def _get_stoken(self, pwd_id: str, passcode: str = "") -> Tuple[bool, Optional[str], Optional[str]]:
        """
        请求 stoken 来验证资源是否有效。
        返回 (ok, stoken, errmsg)
        """
        path = "/1/clouddrive/share/sharepage/token"
        params = {"pr": "ucpro", "fr": "pc"}
        payload = {"pwd_id": pwd_id, "passcode": passcode}

        try:
            resp_json = await self.fetch_json("post", path, params=params, json=payload)
        except aiohttp.ClientError as e:
            logger.warning("请求 stoken 失败（网络层）: %s", e)
            return False, None, f"网络错误: {e}"
        except Exception as e:
            logger.warning("请求 stoken 异常: %s", e)
            return False, None, f"异常: {e}"

        # 根据 Quark 返回体结构判断成功与否（有些接口使用 status，有些使用 code）
        if isinstance(resp_json, dict):
            # 优先检查 status==200 并取 data.stoken
            status = resp_json.get("status") or resp_json.get("code")
            if status == 200 or status == 0:
                data = resp_json.get("data") or {}
                stoken = data.get("stoken")
                if stoken:
                    return True, stoken, None
                else:
                    # 兼容返回 data 为空或字段缺失
                    return False, None, "未在响应中找到 stoken"
            # 返回的 message / msg
            message = resp_json.get("message") or resp_json.get("msg") or str(resp_json)
            return False, None, f"请求被拒绝: {message}"
        else:
            return False, None, "响应不是 JSON 对象"

    async def parse_share_link(self) -> Dict[str, Any]:
        """
        解析分享链接并获取 stoken。
        返回结构:
        {
            "ok": bool,
            "pwd_id": str|None,
            "passcode": str,
            "pdir_fid": str|None,
            "paths": [...],
            "stoken": str|None,
            "error": str|None
        }
        """
        result: Dict[str, Any] = {"ok": False, "error": None}
        self.pwd_id, self.passcode, self.pdir_fid, self.paths = self._extract_url(self.share_link)
        if not self.pwd_id:
            result["error"] = "无法从链接中提取 pwd_id"
            return result

        ok, stoken, err = await self._get_stoken(self.pwd_id, self.passcode)
        if not ok:
            result["error"] = err or "获取 stoken 失败"
            return result

        self.stoken = stoken
        result.update({
            "ok": True,
            "pwd_id": self.pwd_id,
            "passcode": self.passcode,
            "pdir_fid": self.pdir_fid,
            "paths": self.paths,
            "stoken": self.stoken,
            "error": None,
        })
        return result

    async def ls_dir(self, pdir_fid: Optional[str] = None, _fetch_share: int = 0) -> Dict[str, Any]:
        """
        列出目录下文件（支持分页合并）。
        :param pdir_fid: 目录 fid（默认为 parse_share_link 中解析的 pdir_fid）
        :param _fetch_share: 是否同时抓取 share（接口参数）
        :return: 如果成功返回 data（包含 list, metadata 等），失败返回 {"error": "..."}
        """
        if pdir_fid is None:
            pdir_fid = self.pdir_fid
        if not pdir_fid:
            return {"error": "pdir_fid 未指定或未从链接解析到"}

        if not self.stoken:
            return {"error": "stoken 未获取，请先调用 parse_share_link()"}

        list_merge: List[Dict[str, Any]] = []
        page = 1
        try:
            while True:
                path = "/1/clouddrive/share/sharepage/detail"
                params = {
                    "pr": "ucpro",
                    "fr": "pc",
                    "pwd_id": self.pwd_id,
                    "stoken": self.stoken,
                    "pdir_fid": pdir_fid,
                    "force": "0",
                    "_page": page,
                    "_size": "50",
                    "_fetch_banner": "0",
                    "_fetch_share": _fetch_share,
                    "_fetch_total": "1",
                    "_sort": "file_type:asc,file_name:desc",
                }
                resp_json = await self.fetch_json("get", path, params=params)

                # 适配返回结构，判断 code 是否为 0 表示成功
                if not isinstance(resp_json, dict):
                    return {"error": "接口返回非 JSON 或结构异常"}

                if resp_json.get("code") != 0:
                    return {"error": resp_json.get("message") or resp_json.get("msg") or "接口错误"}

                data = resp_json.get("data") or {}
                page_list = data.get("list") or []
                metadata = resp_json.get("metadata") or {}
                list_merge.extend(page_list)

                # 继续分页或终止
                total = metadata.get("_total")
                if not page_list:
                    break
                if total is not None and len(list_merge) >= int(total):
                    break
                page += 1

            # 将合并后的 list 放回 data 里并返回
            data["list"] = list_merge
            data["metadata"] = metadata
            return data
        except aiohttp.ClientError as e:
            logger.exception("ls_dir 网络错误: %s", e)
            return {"error": f"网络错误: {e}"}
        except Exception as e:
            logger.exception("ls_dir 异常: %s", e)
            return {"error": f"异常: {e}"}




# ---------------- 示例用法（供参考） ----------------
# async def example():
#     link = "https://drive-pc.quark.cn/s/abcd1234?pwd=1234"
#     client = QuarkParseClient(link)
#     parse_res = await client.parse_share_link()
#     if not parse_res["ok"]:
#         print("解析失败:", parse_res["error"])
#         await client.close()
#         return
#
#     # 列出目录
#     data = await client.ls_dir(parse_res["pdir_fid"])
#     if data.get("error"):
#         print("列目录失败:", data["error"])
#     else:
#         print("文件列表数量:", len(data.get("list", [])))
#         # 遍历文件 list 做进一步处理
#
#     await client.close()
async def main():
    setup_logging()
    client = QuarkParseClient('https://pan.quark.cn/s/969ddab7b51e')
    result= await client.parse_share_link()
    ls_result=await client.ls_dir('0')
    print(result)
    print(ls_result)
if __name__ == '__main__':
    asyncio.run(main())