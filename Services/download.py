import asyncio
import json
from pathlib import Path

import requests
from aiohttp import ClientSession
from sqlmodel import Session, select

import settings
from QuarkDisk import QuarkDisk
from database import engine
from models.resource import Resource
from server import quark_disk
from utils import get_cookie_str


class Aria2Download:
    def __init__(self):
        self.api = "http://192.168.31.201:6800/jsonrpc"
        # 消息id，aria2会原样返回这个id，可以自动生成也可以用其他唯一标识
        self.id = "QXJpYU5nXzE2NzUxMzUwMDFfMC42Mzc0MDA5MTc2NjAzNDM="
        self.session=ClientSession()
    async def close(self):
        await self.session.close()
    async   def addUri(self, url, path,headers, file=None, proxy=None,):
        """
        添加任务
        :param headers:
        :param url: 文件下载地址
        :param path: 文件保存路径
        :param file: 文件保存名称
        :param proxy: 代{过}{滤}理地址
        :return:
        """
        data = {
            "id": self.id,
            "jsonrpc": "2.0",
            "method": "aria2.addUri",
            "params": ["token:123",[url], {"dir": path, "out": file, "all-proxy": proxy,"header":headers}]
        }
        async with self.session.post(self.api, json=data) as resp:

            # print("addUri", return_json)
            return await resp.json()
    async def on_download_complete(self, gid):
        """
        当下载完成时，触发的回调函数。
        :param gid: 下载任务的 GID（任务标识符）
        """
        print(f"Download completed. GID: {gid}")
        # 你可以在这里处理下载完成后的逻辑，例如移动文件，解压缩，发送通知等。
    # 订阅下载事件
    async def subscribe_download_events(self):
        subscription_payload = {
            "jsonrpc": "2.0",
            "method": "aria2.onDownloadComplete",
            "id": self.id,
            "params": ['on_download_complete']
        }

        async with self.session.post(self.api, json=subscription_payload) as response:
            result = await response.json()
            print(f"Subscribed to download complete event: {result}")
    async  def getGlobalStat(self):
        """
        获取全部下载信息
        :return:
        """
        data = {
            "jsonrpc": "2.0",
            "method": "aria2.getGlobalStat",
            "id": self.id,
            "params": ["token:fnos"]
        }
        async with self.session.post(self.api, json=data) as response:
            resp_json = await response.json()
            # print("getGlobalStat", return_json)
            return resp_json

    async  def tellActive(self):
        """
        正在下载
        :return:
        """
        data = {
            "jsonrpc": "2.0",
            "method": "aria2.tellActive",
            "id": self.id, "params": [
                ["gid", "totalLength", "completedLength", "uploadSpeed", "downloadSpeed", "connections",
                 "numSeeders",
                 "seeder", "status", "errorCode", "verifiedLength", "verifyIntegrityPending", "files", "bittorrent",
                 "infoHash"]]
        }
        async with self.session.post(self.api, json=data) as response:
            resp_json = await response.json()
            # print("getGlobalStat", return_json)
            return resp_json

    async  def tellWaiting(self):
        """
        正在等待
        :return:
        """
        data = {"jsonrpc": "2.0", "method": "aria2.tellWaiting",
                "id": self.id,
                "params": [0, 1000, ["gid", "totalLength",
                                     "completedLength",
                                     "uploadSpeed",
                                     "downloadSpeed",
                                     "connections",
                                     "numSeeders",
                                     "seeder", "status",
                                     "errorCode",
                                     "verifiedLength",
                                     "verifyIntegrityPending"]
                           ]
                }
        async with self.session.post(self.api, json=data) as response:
            resp_json = await response.json()
            # print("getGlobalStat", return_json)
            return resp_json

    async  def tellStopped(self):
        """
        已完成/已停止
        :return:
        """
        data = {"jsonrpc": "2.0",
                "method": "aria2.tellStopped",
                "id": self.id,
                "params": [-1, 1000, ["gid", "totalLength",
                                      "completedLength",
                                      "uploadSpeed",
                                      "downloadSpeed",
                                      "connections",
                                      "numSeeders", "seeder",
                                      "status", "errorCode",
                                      "verifiedLength",
                                      "verifyIntegrityPending"]]
                }
        async with self.session.post(self.api, json=data) as response:
            resp_json = await response.json()
            # print("getGlobalStat", return_json)
            return resp_json

    async def tellStatus(self, gid):
        """
        任务状态
        :param gid: 任务ID
        :return:
        """
        data = {"jsonrpc": "2.0", "method": "aria2.tellStatus", "id": self.id, "params": [gid]}
        async with self.session.post(self.api, json=data) as response:
            resp_json = await response.json()
            # print("getGlobalStat", return_json)
            return resp_json

    async def removeDownloadResult(self, gid):
        """
        删除下载结束的任务
        :param gid: 任务ID
        :return:
        """
        data = {"jsonrpc": "2.0", "method": "aria2.removeDownloadResult", "id": self.id, "params": [gid]}
        async with self.session.post(self.api, json=data) as response:
            resp_json = await response.json()
            # print("getGlobalStat", return_json)
            return resp_json
class DownLoad:
    def __init__(self,quark_disk:QuarkDisk):
        self.quark_disk = quark_disk
        # 获取当前脚本文件所在的目录
        current_path = Path(__file__).resolve().parent.parent
        self.download_base_path =f"{str(current_path)}/downloads"
        print(current_path)
        self.aria2=Aria2Download()
        pass
    async   def download(self,name,download_url,cookie):
        # fid=await self.quark_disk.get_fids(['/资源分享/热门-国产剧/借命而生(2025)'])
        # ls_list=await self.quark_disk.ls_dir(fid[0]['fid'])
        #
        # fid_list=[i['fid'] for i in ls_list if i['file_name']=='Fiddler Everywhere 5.19.0.zip']
        #
        # result,cookie=await self.quark_disk.download(fid_list)
        # print(json.dumps(result,indent=4,ensure_ascii=False))
        # download_url=result['data'][0]['download_url']
        # fid=result['data'][0]['fid']
        # f_name=result['data'][0]['file_name']
        # save_name=f"{fid}-{f_name}"
        # print(download_url,self.download_base_path,save_name)
        # headers=[f"Cookie: b-user-id=29cee579-37cd-2713-1a77-f43a0518e2ca;"
        #          f" __kps=AAT2Tergi2YkOZnzCPxQyzdZ; __ktd=kCbFlepz08rSgrlrVnzr6Q==;"
        #          f" __uid=AAT2Tergi2YkOZnzCPxQyzdZ;"
        #          f" isg=BN_f7MI7y4ZCcMD5igre-i7FbjNpRDPm1Ri5snEtvg6MAPyCeRWfN14Zxph-mAte;"
        #          f" tfstk=gi2-XicjSZboVTHGET1DtkzvaRI0vJEzkzr6K20kOrUYYyhnObmopXaSo8cnF44xGcoMVMkCajOL-0T7FYahp2ZZuL4haXvp4-U9KLbPak9KKv_GSOXg4uDEdNj1HFcvzDi6R9cIVtMrxLWrn06g4u-X2esgGOxLqos7V2aINjMjxqtSAyGSGogqYDTSALsYcqujVUGINqGj40pIAyMCDogqAvgILqj-u3iJp5JY_pbC8MdBO-n-w2pokpH_ndco5rgvdNNt2zg_VqpBd42kxkqYqapamYrbWc4lhLUTb-zxcP6dkvz4OyiLlO8nU54zQjEV1KZmeqlsf-sBC228ilgxBH67DY3-18cWjd4_DkNiM-j1QYHSPWDzxhQuD8Uu4-EHAIM-EShTeA6wP2V0XJnLLwWYWly4kma1paszcR29nTYiWDA5DideTbiVWNmUag2hcpmxSgGWTBln0m3GD5deTbG-DVj-pBREiR5..;"
        #          f" __pus=f963d4314a6823d5c04431f6c4c7f3d1AAToL03aIymltmhzHag9mGYudd9w8CG9ZYuixKpgqhxOLUF1i/0gpLM8/z5vFFYp7JFsvOhjJVvViYWXUF1hayfc;"
        #          f" __kp=a3344700-25a1-11f0-91d0-4b0aeb89fee0;"
        #          f" __puus=e0f6b83f8ffe3632b5789e86653a52aeAASe4D44NBAPorJd6E1Kr7SfCKweaRCfqq0B2447+WQ5C/rQCltzStAyjJCRnK2MOFO3KaVKrLt1E8dRbVEEqpjHRttrujS2X7zwUCrsDlHqxvrhiPXH1YdX7Hg5Uw5ShU51nDMaQVjZ0pD0Bt3K9Jczpgb1J9SM9wJTLdeUNYpZQeK2hcPrxA8zjsBhN5peb468m5F+fA/P4YOVuH7b9A+8"
        #          ]
        headers=[f"Cookie: {cookie}"]
        result=await  self.aria2.addUri(download_url,self.download_base_path,headers=headers,file=name,)

        print(result)

    import requests
    import json
    async def test(self):
        result= await self.aria2.getGlobalStat()
        print(json.dumps(result,indent=4,ensure_ascii=False))
    async def close(self):
        await self.aria2.close()
    async def get_finished(self):
        # 获取所有文件
        files = [str(f.resolve()) for f in Path(self.download_base_path).iterdir() if f.is_file()]
        files_=[f for f in files if   f.endswith('.aria2')==False]
        finished_files=[f for f in files_ if f"{f}.aria2" not in files]
        print(json.dumps(finished_files,indent=4,ensure_ascii=False))

async def down_risk_files(quark_disk:QuarkDisk,download:DownLoad):
    with Session(engine) as session:
        resources= session.exec(select(Resource).where((Resource.has_detect_risk != None)&(Resource.has_detect_risk==True)).order_by(Resource.douban_last_async.desc().nulls_last()).limit(settings.select_resource_num)).all()
        files=[]

        for resource in resources:
            risk_files= resource.risk_file
            files.extend([{'title':resource.title,'file':i} for i in risk_files])

        fid_list=[f['file']['fid'] for f in files]
        download_info_list,cookie_= (await  quark_disk.download(fid_list))
        files_map={
            i['file']['fid']:i for i in files
        }
        for i in download_info_list['data']:
            _fid=i['fid']
            _title=files_map[_fid]['title']
            _file_name=i['file_name']
            down_name=f"{_title}-{_fid}-{_file_name}"
            url=i['download_url']
            cookie=cookie_ or await get_cookie_str(quark_disk.session)
            await  download.download(down_name,url,cookie)
        # download_fids=[f['fid'] for f in download_info_list]
        # print(json.dumps(download_fids,indent=4,ensure_ascii=False))

async def main():
    quark_disk = QuarkDisk(settings.STORAGE_CONFIG['quark'][0])
    await quark_disk.connect()
    download = DownLoad(quark_disk)
    # await  download.download('','')
    # await download.test()
    await download.get_finished()
    # await down_risk_files(quark_disk,download)
    await quark_disk.close()
    await download.close()
if __name__ == '__main__':
   asyncio.run(main())