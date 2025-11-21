import asyncio
import json
import logging
import random
import time
from datetime import datetime
from typing import Optional, Dict


from app.core.abc_aio_client import BaseAioClient
from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import PanCloud

from app.utils.cache import async_ttl_cache
from app.utils.tools import make_cookiejar

logger=logging.getLogger(__name__)
class QuarkCloudClient(BaseAioClient):
    def __init__(self,pancloud_name:str,cookies_str:str):

        self.BASE_URL='https://drive-pc.quark.cn'
        self.headers = {}
        self.cookies_str = cookies_str
        self.pancloud_name=pancloud_name
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()
        super().__init__()
        # 注册 context（仅注册，不创建 session）
        USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) quark-cloud-drive/3.14.2 Chrome/112.0.5615.165 Electron/24.1.3.8 Safari/537.36 Channel/pckk_other_ch"
        super().init(
            name=self.pancloud_name,
            base_url=self.BASE_URL,
            headers={"User-Agent": USER_AGENT,
                     "accept": "application/json, text/plain, */*",
                     "origin": "https://pan.quark.cn",
                     "referer": "https://pan.quark.cn/",
                     "x-request-id": str(random.randint(10 ** 15, 10 ** 16 - 1)),
                     },
            cookie_jar=make_cookiejar(self.cookies_str),
        )






    async def connect(self):
        url = "https://pan.quark.cn/account/info"
        params = {
            'fr': 'pc',
            'platform': 'pc'
        }
        async with await self.request(method="GET", url=url, params=params) as resp:
            try:
                data = await resp.json()
                logger.info(data)
                if data["success"]:
                    logger.info(f'已成功连接{data['data']['nickname']}')
                    return True
                else:
                    logger.error(f'|{self.pancloud_name}|连接失败:{data}')
                    return False

            except Exception as e:
                logger.error(e)
                return e

    async def request(self, method: str, url: str, *, params=None, data=None, json=None, headers=None,**kwargs):

        # 限速逻辑
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            min_interval = 1.0  # 最少间隔 1 秒

            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)

            self._last_request_time = time.monotonic()
            # 合并默认 params 和调用时传入的 params
            session=await self.get_session()
            session.headers.update({"x-request-id": str(random.randint(10 ** 15, 10 ** 16 - 1)), })

            # return await session.request(method, url, params=params, data=data, json=json, headers=headers)
            return await super().request(method, url, params=params, data=data, json=json, headers=headers,as_type='resp', **kwargs)



    async  def ls_dir(self, pdir_fid, **kwargs):
        file_list = []
        page = 1
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/file/sort"
            querystring = {
                "pr": "ucpro",
                "fr": "pc",
                "uc_param_str": "",
                "pdir_fid": pdir_fid,
                "_page": page,
                "_size": "50",
                "_fetch_total": "1",
                "_fetch_sub_dirs": "0",
                "_sort": "file_type:asc,file_name:desc",
                "_fetch_full_path": kwargs.get("fetch_full_path", 0),
            }
            async with await self.request(method="GET", url=url, params=querystring) as resp:
                resp_json = await resp.json()
                if resp_json["code"] != 0:
                    return {"error": resp_json["message"]}
                if resp_json["data"]["list"]:
                    file_list += resp_json["data"]["list"]
                    page += 1
                else:
                    break
                if len(file_list) >= resp_json["metadata"]["_total"]:
                    break
        print(file_list)
        return file_list

    async def download(self, fids):
        url = f"{self.BASE_URL}/1/clouddrive/file/download"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"fids": fids}
        async with await self.request(method="POST", url=url, params=querystring,json=payload) as resp:
            set_cookie_headers = resp.headers.get('Set-Cookie')
            # cookie_str = "; ".join([f"{key}={value}" for key, value in set_cookie.items()])
            return await resp.json(), set_cookie_headers

    async  def get_fids(self, file_paths:list[str]):
        """
        批量根据文件路径获取文件fid
        :param file_paths:
        :return:
         """

        fids = []
        # for file_path in file_paths:
        #     if self.fid_cache.get(file_path) is not None:
        #         fids.append( self.fid_cache[file_paths])
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/file/info/path_list"
            querystring = {"pr": "ucpro", "fr": "pc"}
            payload = {"file_path": file_paths[:50], "namespace": "0"}
            async with await self.request(method="post", url=url, params=querystring,json=payload) as resp:
                print(await resp.text())
                resp_json = await resp.json()
                if resp_json["code"] == 0:
                    fids += resp_json["data"]
                    file_paths = file_paths[50:]
                else:
                    logger.info(f"获取目录ID：失败, {resp_json['message']}")
                    raise RuntimeError(f"获取目录ID：失败, {resp_json['message']}")
                if len(file_paths) == 0:
                    break

        return fids

    async def mkdir(self, dir_path:str)->bool:
        """
        可跨级创建目录
        :param dir_path:例如：‘/1级目录/2级目录’
        :return:true/false
        """
        url = f"{self.BASE_URL}/1/clouddrive/file"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {
            "pdir_fid": "0",
            "file_name": "",
            "dir_path": dir_path,
            "dir_init_lock": False,
        }
        async with await self.request(method="post",params=querystring, url=url, json=payload) as resp:
            resp_json = await resp.json()
            if resp_json["code"] == 0:

                return resp_json["data"]["finish"]
            else:
                raise Exception(f'创建{dir_path}失败：{resp.text}')

    async   def _save_file(self, fid_list, fid_token_list, to_pdir_fid, pwd_id, stoken):
        url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/save"
        querystring = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "app": "clouddrive",
            "__dt": int(random.uniform(1, 5) * 60 * 1000),
            "__t": datetime.now().timestamp(),
        }
        payload = {
            "fid_list": fid_list,
            "fid_token_list": fid_token_list,
            "to_pdir_fid": to_pdir_fid,
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": "0",
            "scene": "link",
        }
        async with await self.request(method="post", url=url, params=querystring, json=payload) as resp:
            resp_json = await resp.json()

            return resp_json

    async def _query_task(self, task_id):
        retry_index = 0
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/task"
            querystring = {
                "pr": "ucpro",
                "fr": "pc",
                "uc_param_str": "",
                "task_id": task_id,
                "retry_index": retry_index,
                "__dt": int(random.uniform(1, 5) * 60 * 1000),
                "__t": datetime.now().timestamp(),
            }
            async with await self.request(method="get", url=url, params=querystring) as resp:
                resp_json = await resp.json()
                if resp_json["data"]["status"] != 0:
                    if retry_index > 0:
                        print()
                    break
                else:
                    if retry_index == 0:
                        print(
                            f"正在等待[{resp_json['data']['task_title']}]执行结果",
                            end="",
                            flush=True,
                        )
                    else:
                        print(".", end="", flush=True)
                    retry_index += 1
                    await asyncio.sleep(0.5)
        return resp_json

    async def save_file(self,fid_list, fid_token_list, to_pdir_fid:str, pwd_id, stoken):

        save_file_return =await self._save_file(
            fid_list, fid_token_list, to_pdir_fid, pwd_id, stoken
        )
        err_msg = None
        if save_file_return["code"] == 0:
            task_id = save_file_return["data"]["task_id"]
            query_task_return =await self._query_task(task_id)
            if query_task_return["code"] == 0:

                return True
            else:
                err_msg = query_task_return["message"]
        else:
            err_msg = save_file_return["message"]
        if err_msg:
            raise Exception(err_msg)
    async def rename(self, fid, file_name):
        url = f"{self.BASE_URL}/1/clouddrive/file/rename"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"fid": fid, "file_name": file_name}
        # s=await self.get_session()
        # async with await  s.request(method="post", url=url, params=querystring, json=payload)as resp:
        #     resp_json = await resp.json()
        #     return resp_json

        async with await self.request(
            "POST", url, json=payload, params=querystring
        ) as resp:
            response =await resp.json()
            try:
                if response["status"] ==200 :
                    return True
                else:
                    raise Exception(f'重命名发生错误：{response}')
            except Exception as e:

                raise Exception(f'重命名发生错误：{response}')

    async def delete(self, fid_list: [], action_type: int = 2) -> bool:
        """
        删除指定路径的文件或文件夹。
        根据 API 响应，此操作是异步的。

        Args:
            fid_list: 要删除的文件或文件夹 fid
            action_type: 删除类型，默认为 2 (根据示例推测为移入回收站)。

        Returns:
            True 如果删除任务成功完成，否则 False。
        """
        # 2. Prepare API call
        url = f"{self.BASE_URL}/1/clouddrive/file/delete"
        params = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {
            "action_type": action_type,
            "filelist": fid_list,  # API expects a list of FIDs
            "exclude_fids": []  # Based on example
        }

        async with await self.request("POST", url, json=payload, params=params) as resp:
            task_id = None
            text=await resp.text()
            if resp.status == 200:
                try:
                    data =await resp.json()
                    # Check API code and if task_id exists
                    if data.get("data", {}).get("task_id"):
                        task_id = data["data"]["task_id"]
                    else:
                        # API returned an error in the initial call
                        print()
                        raise RuntimeError(f"提交删除任务失败: {data.get('message', '未知 API 错误')} (Code: {data.get('code')})")
                except json.JSONDecodeError:
                    raise RuntimeError(f"提交删除任务失败: 响应不是有效的JSON - {text[:100]}")
            else:
                raise RuntimeError(f"提交删除任务失败: HTTP {resp.status} - {text[:100]}")

            if not task_id:
                raise RuntimeError("未能获取删除任务的 Task ID。")

            task_result =await self._query_task(task_id)
            if task_result is None:
                raise RuntimeError("查询删除任务状态失败或超时。")
            task_data = task_result.get("data", {})
            task_status = task_data.get("status")
            if task_status != 0:  # Status 1 typically means success for tasks
                return True
            else:
                raise RuntimeError(f"删除任务失败或未成功完成,最终任务状态: {task_status}")


    async def _get_share_details(self, share_id: str) -> Optional[Dict]:
        """Internal: Retrieves share details (including URL) using the share_id."""
        if not share_id: return None
        # print(f"正在使用 Share ID '{share_id}' 获取分享链接详情...")
        url = f"{self.BASE_URL}/1/clouddrive/share/password" # Endpoint from user example
        params = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"share_id": share_id}

        async with await self.request("POST", url, json=payload, params=params) as resp:

            if resp.status == 200:
                try:
                    data =await resp.json()
                    # Check API code for success
                    if data.get("code") == 0 and data.get("data"):
                        # print("获取分享链接详情成功。")
                        return data.get("data") # Return the nested 'data' dictionary
                    else:
                        raise RuntimeError(f"获取分享链接详情 API 返回错误: {data.get('message', '未知错误')} (Code: {data.get('code')}) - Share ID: {share_id}")
                except json.JSONDecodeError:
                    raise RuntimeError('f"获取分享链接详情失败: 响应不是有效的JSON - {resp.text[:100]} - Share ID: {share_id}"')
            else:
                raise RuntimeError('f"获取分享链接详情失败: HTTP {resp.status_code} - {resp.text[:100]} - Share ID: {share_id}"')

    async def create_share_link(self, fid_list: [], title: str=None, password: Optional[str] = None, expired_type: int = 1,
                          url_type: int = 1) -> Optional[str]:
        """
        为用户网盘中的文件或文件夹创建公开分享链接，并返回最终的分享 URL。

        Args:
            fid_list: 要分享的文件或文件夹在 fid
            title: 分享链接的标题。
            password: (可选) 为分享设置的密码。如果为 None，则不设置密码。
            expired_type: (可选) 链接过期类型，默认为 1 (可能 1=永久, 其他值待探索)。
            url_type: (可选) 链接 URL 类型，默认为 1 (具体含义需探索)。

        Returns:
            成功时返回最终的分享 URL (e.g., "https://pan.quark.cn/s/...") 字符串，
            失败时返回 None。
        """
        init_url = f"{self.BASE_URL}/1/clouddrive/share"
        params = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {
            "fid_list": fid_list, "title": title,
            "url_type": url_type, "expired_type": expired_type,
        }
        if password:
            # Confirmed key based on get_stoken and common patterns
            payload["passcode"] = password
        # 3. Send Request to initiate share
        async with await self.request("POST", init_url, json=payload, params=params) as resp:
            # 4. Process Initiation Response
            task_id = None
            text=await resp.text()
            if resp.status == 200:
                try:
                    init_data =await resp.json()
                    if init_data.get("code") == 0 and init_data.get("data", {}).get("task_id"):
                        task_id = init_data["data"]["task_id"]
                        # print(f"创建分享链接请求已提交。 Task ID: {task_id}")
                    else:

                        raise RuntimeError(f"创建分享链接 API (步骤 1) 返回错误: {init_data.get('message', '未知错误')} (Code: {init_data.get('code')})")
                except json.JSONDecodeError:
                    print()
                    raise RuntimeError(f"创建分享链接失败 (步骤 1): 响应不是有效的JSON - {text[:100]}")
            else:
                raise RuntimeError(f"创建分享链接失败 (步骤 1): HTTP {resp.status} - {text[:100]}")

            if not task_id: return None  # Should not happen if code above is correct

            # 5. Poll the task status to get share_id
            task_result =await self._query_task(task_id)

            if task_result is None:
                raise RuntimeError("查询分享任务状态失败或超时。")

            message=task_result["message"]
            code=task_result["code"]
            if code == 0:
                task_data = task_result.get("data", {})
                # Extract share_id from the successful task data
                share_id = task_data.get("share_id")
                if not share_id:
                    raise RuntimeError(f"分享任务成功完成，但响应中未找到 share_id。 Task Data: {task_data}")
                try:
                    share_details =await self._get_share_details(share_id)
                except Exception as e:
                    raise e
                # 7. Extract and return the share URL
                final_share_url = share_details.get("share_url")
                if not final_share_url:
                    raise RuntimeError(f"获取分享详情成功，但响应中未找到 share_url。 Details: {share_details}")
                return final_share_url

            else:   raise RuntimeError(json.dumps({
                    'code':code,
                    'message':message,
                },ensure_ascii=False))


    async def move(self,fid_list:[],pdir_fid:str):
        url = f"{self.BASE_URL}/1/clouddrive/file/move"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"filelist": fid_list, "to_pdir_fid": pdir_fid}
        async with await self.request(
                "POST", url, json=payload, params=querystring
        ) as resp:

            try:
                response = await resp.json()
                task_id = response["data"]["task_id"]
                task_result = await self._query_task(task_id)
                code=task_result["code"]
                if code == 0:
                    status = task_result["data"]["status"]
                    if status==2:
                        return True
                raise RuntimeError(f'移动文件发生错误{task_result}')
            except Exception as e:
                raise Exception(f"{str(e)  }{await resp.text()}")


@async_ttl_cache(key_fields=['name'])
async def get_quark_cloud_client(pancloud:PanCloud):
    logger.debug(f'开始获取{pancloud.name}的夸克client')
    name=pancloud.name
    cookies=pancloud.cookie
    return QuarkCloudClient(name, cookies)
async def main():
    await init_db()
    setup_logging()
    p=await PanCloud.find_one(PanCloud.name=='4295quark')
    r=  await get_quark_cloud_client(p)
    res= await r.connect()
    # res= await r.ls_dir(pdir_fid='asdasd')
    res=await r.rename(fid='ce2d61b4a2ac41e8b8a8299c7f91142d',file_name='修改后的名称12356733.mkv')
    print(res)

if __name__ == "__main__":
    asyncio.run(main())

