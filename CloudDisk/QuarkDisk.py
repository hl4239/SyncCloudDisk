import asyncio
import json
import logging
import random
import re
import urllib
from abc import ABC, abstractmethod
from datetime import datetime

import aiohttp

import settings


class DiskBase(ABC):
    USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) quark-cloud-drive/3.14.2 Chrome/112.0.5615.165 Electron/24.1.3.8 Safari/537.36 Channel/pckk_other_ch"
    BASE_URL = "https://drive-pc.quark.cn"
    def __init__(self,config: dict[str, any]):
        self.config = config
        self.connected = False
        self.name=config["name"]
        self.logger = logging.getLogger(f"DiskLogger-{self.name}")
        self.logger.setLevel(logging.DEBUG)

        # 避免重复添加 Handler（尤其是多次初始化时）
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)

            formatter = logging.Formatter(
                f"[%(asctime)s] [%(levelname)s] [{self.name}] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

    def debug(self, msg): self.logger.debug(msg)

    def info(self, msg): self.logger.info(msg)

    def warning(self, msg): self.logger.warning(msg)

    def error(self, msg): self.logger.error(msg)

    def critical(self, msg): self.logger.critical(msg)

    @abstractmethod
    def connect(self)->bool:
        pass
class ParseQuarkShareLInk:
    def __init__(self,link:str):
        self.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) quark-cloud-drive/3.14.2 Chrome/112.0.5615.165 Electron/24.1.3.8 Safari/537.36 Channel/pckk_other_ch"
        self.BASE_URL = "https://drive-pc.quark.cn"
        self.share_link = link
        self.session=None
        self.pdir_fid=None
        self.pwd_id=None
        self.passcode=None
        self._=None
        self.stoken=None
        self._init_session()
    def _init_session(self):
        headers={
            "User-Agent":self.USER_AGENT,
            "Referer":self.BASE_URL,

        }
        self.session=aiohttp.ClientSession(headers=headers)


    def _extract_url(self, url):
        # pwd_id
        match_id = re.search(r"/s/(\w+)", url)
        pwd_id = match_id.group(1) if match_id else None
        # passcode
        match_pwd = re.search(r"pwd=(\w+)", url)
        passcode = match_pwd.group(1) if match_pwd else ""
        # path: fid-name
        paths = []
        matches = re.findall(r"/(\w{32})-?([^/]+)?", url)
        for match in matches:
            fid = match[0]
            name = urllib.parse.unquote(match[1])
            paths.append({"fid": fid, "name": name})
        pdir_fid = paths[-1]["fid"] if matches else 0
        return pwd_id, passcode, pdir_fid, paths

    async  def _get_stoken(self,pwd_id, passcode=""):
        """
        可验证资源是否失效
        :param pwd_id:
        :param passcode:
        :return: 返回 trye,stoken 或 false,errormessage
        """
        url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/token"
        querystring = {"pr": "ucpro", "fr": "pc"}
        payload = {"pwd_id": pwd_id, "passcode": passcode}
        async with await self.session.request(method="post", url=url, params=querystring,json=payload) as resp:
            resp_json = await resp.json()

            if resp_json.get("status") == 200:
                return True, resp_json["data"]["stoken"]
            else:
                return False, resp_json["message"]

    async def parse_share_link(self):
        result={}
        self.pwd_id,self.passcode,self.pdir_fid,self._=self. _extract_url(self.share_link)
        self._,self.stoken = await self._get_stoken(self.pwd_id,self.passcode)



    async def ls_dir(self,pdir_fid:str,_fetch_share=0):
        list_merge = []
        page = 1
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/detail"
            querystring = {
                "pr": "ucpro",
                "fr": "pc",
                "pwd_id":self.pwd_id,
                "stoken":self. stoken,
                "pdir_fid":pdir_fid,
                "force": "0",
                "_page": page,
                "_size": "50",
                "_fetch_banner": "0",
                "_fetch_share": _fetch_share,
                "_fetch_total": "1",
                "_sort": "file_type:asc,file_name:desc",
            }
            async with await self.session.request(method="get", url=url, params=querystring) as resp:
                resp_json = await resp.json()
                if resp_json["code"] != 0:
                    return {"error": resp_json["message"]}
                if resp_json["data"]["list"]:
                    list_merge += resp_json["data"]["list"]
                    page += 1
                else:
                    break
                if len(list_merge) >= resp_json["metadata"]["_total"]:
                    break
        resp_json["data"]["list"] = list_merge

        return resp_json["data"]

    async def close(self):
        await self.session.close()

class QuarkDisk(DiskBase):


    def __init__(self,config: dict[str, any]):
        self.cookie=config["cookie"]
        self.session=None

        self.mparam=self._parse_mparam_from_cookie()
        self.fid_cache:dict[str, str]={"/":"0"}
        super().__init__(config)
        self._init_session()
    async  def close(self):
        await self.session.close()
    def _init_session(self):

        if not self.session:
            self.session= aiohttp.ClientSession(
                headers={"User-Agent":self.USER_AGENT,
                         'Cookie':self.cookie, "accept": "application/json, text/plain, */*",
            "origin": "https://pan.quark.cn",
            "referer": "https://pan.quark.cn/",
            "x-request-id": str(random.randint(10**15, 10**16 - 1)),
                         },

            )
    def _parse_mparam_from_cookie(self) -> dict[str, str]:
        mparam = {}
        kps_match = re.search(r"(?<!\w)kps=([a-zA-Z0-9%+/=]+)[;&]?", self.cookie)
        sign_match = re.search(r"(?<!\w)sign=([a-zA-Z0-9%+/=]+)[;&]?", self.cookie)
        vcode_match = re.search(r"(?<!\w)vcode=([a-zA-Z0-9%+/=]+)[;&]?", self.cookie)
        if kps_match and sign_match and vcode_match:
            mparam = {
                "kps": kps_match.group(1).replace("%25", "%"),
                "sign": sign_match.group(1).replace("%25", "%"),
                "vcode": vcode_match.group(1).replace("%25", "%"),
            }
        return mparam
    async def _request(self, method: str, url: str, *,
                       params=None, data=None, json=None, headers=None):

        self.session.headers.update({ "x-request-id": str(random.randint(10**15, 10**16 - 1)),})
        # 合并默认 params 和调用时传入的 params




        return await  self.session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json
        )

    async  def connect(self) -> bool:
        url="https://pan.quark.cn/account/info"
        params={
            'fr':'pc',
            'platform':'pc'
        }
        async with await self._request(method="GET", url=url, params=params) as resp:
            try:

                data = await resp.json()
                if data["success"] :
                    self.logger.info(f'已成功连接{data['data']['nickname']}')
            except Exception as e:
                self.logger.error(e)

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
            async with await self._request(method="GET", url=url, params=querystring) as resp:
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
        return file_list


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
            async with await self._request(method="post", url=url, params=querystring,json=payload) as resp:
                resp_json = await resp.json()
                if resp_json["code"] == 0:
                    fids += resp_json["data"]
                    file_paths = file_paths[50:]
                else:
                    self.logger.info(f"获取目录ID：失败, {resp_json['message']}")
                    break
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
        async with await self._request(method="post",params=querystring, url=url, json=payload) as resp:
            resp_json = await resp.json()
            if resp_json["code"] == 0:

                return resp_json["data"]["finish"]
            else:
                self.logger.info(f'创建{dir_path}失败：{resp.text}')

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
        async with await self._request(method="post", url=url, params=querystring, json=payload) as resp:
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
            async with await self._request(method="get", url=url, params=querystring) as resp:
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

                self.logger.info(f'✅转存成功\n')
            else:
                err_msg = query_task_return["message"]
        else:
            err_msg = save_file_return["message"]
        if err_msg:
            self.logger.error(f"❌转存失败：{err_msg}\n")


    @staticmethod
    async  def parse_share_url(shari_link:str)->ParseQuarkShareLInk:
        parse= ParseQuarkShareLInk(shari_link)
        await parse.parse_share_link()
        return parse



async def main():
    quark_cloud=QuarkDisk(settings.STORAGE_CONFIG['quark'][0])
    await quark_cloud.connect()
    # await quark_cloud.ls_dir(0)
    parse_share= await  QuarkDisk.parse_share_url('https://pan.quark.cn/s/8a4d9ed0c8b6')
    d1=(await parse_share.ls_dir('0'))['list'][0]
    d2=(await parse_share.ls_dir(d1['fid']))['list'][0]
    fid_list=[d2['fid']]
    fid_token_list=[d2['share_fid_token']]
    pdir_fid_list=await  quark_cloud.get_fids([settings.STORAGE_BASE_PATH])
    print(pdir_fid_list)
    pdir_fid=pdir_fid_list[0]['fid']
    save=await quark_cloud.save_file(fid_list,fid_token_list,pdir_fid,parse_share.pwd_id,parse_share.stoken)
    print(save)



    await  quark_cloud.close()
    await parse_share.close()
if __name__ == "__main__":
    asyncio.run(main())