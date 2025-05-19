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
from utils import get_cookie_str


class Aria2API:
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

    async def download_magnet(self,magnet_link, output_dir:str):
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
            "params": [
                f"token:your_secret",  # 如果设置了 RPC 密码
                [magnet_link],
                {
                    "dir": output_dir,
                    "bt-save-metadata": 'true',
                    "bt-metadata-only": 'true',
                    "follow-torrent": 'false',
                }
            ]
        }
        async with self.session.post(self.api, json=data) as resp:
            # print("addUri", return_json)
            return await resp.json()

    async def magnet_to_torrent(self,magnet:str,path:str):
        resp_json = await self.download_magnet(magnet,path)
        task_id=resp_json['result']
        return task_id





async def main():
   aria2=Aria2API()
   # result= await aria2.magnet_to_torrent('magnet:?xt=urn:btih:8172e8456fef02a96bdae79222664749ae5eb469&dn=%E6%8A%98%E8%85%B001.mp4','/vol2/1000/downloads/asda')
   # print(result)
   # while True:
   #     result=await aria2.tellStopped()
   #     print(result)
   #     await asyncio.sleep(1)
   result=await aria2.tellStatus('a9bdf606f2c23841')
   result1= await aria2.tellStopped()
   print(result)
   print(result1)
if __name__ == '__main__':
   asyncio.run(main())