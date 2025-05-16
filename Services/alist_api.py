import re
from itertools import groupby
from tokenize import group

import aiohttp
import asyncio
import json
import os
import traceback # 用于打印详细错误堆栈

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

import settings
from database import engine
from models.resource import Resource


class AlistAPI:
    def __init__(self):
        self.base_url = settings.alist.get('url')  # AList 访问地址
        self.token = settings.alist.get('key')  # AList API Token
        # 构建通用的请求头
        self.headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }
        self.session = aiohttp.ClientSession(headers=self.headers)

    async def copy(self, path_list:[],base_src:str,base_dst:str) :
        """
        从一个存储转存到另一个存储
        """

        api_endpoint = f"{self.base_url}/api/fs/copy"
        # 从完整源路径中智能分离出父目录和最后一级的名称（文件或目录名）
        # 使用 os.path 更可靠地处理各种路径情况

        src_list=[
            {
                'src_pdir_name':os.path.dirname(i['src_path']),
                'src_item_name':os.path.basename(i['src_path']),
                'dst_pdir_name':i['dst_pdir_path'],

            }
            for i in path_list
        ]
        # 首先按照 pdir_name 排序（groupby 要求输入是已排序的）
        src_list_sorted = sorted(src_list, key=lambda x: x['src_pdir_name'])

        # 然后分组
        grouped = {
            key: [i for i in list(group)]
            for key, group in groupby(src_list_sorted, key=lambda x: x['src_pdir_name'])
        }
        result_json={
            'code': 0,
            'message':'',
            'data':{
                'tasks':[]
            }
        }
        for k,v in grouped.items():

            payload = {
                "src_dir": f"/{base_src}{k}",
                # 确保目标目录路径末尾没有斜杠，AList API 可能需要这种格式
                "dst_dir": f"/{base_dst}{v[0]['dst_pdir_name']}",
                "names": [p['src_item_name'] for p in v], # `names` 是一个列表，即使只复制一项
                "overwrite":True
            }

            async with self.session.post(api_endpoint, headers=self.headers, json=payload) as response:
                try:
                 resp_json=   (await response.json())
                 result_json['code'] = resp_json['code']
                 result_json['message'] = resp_json['message']
                 result_json['data']['tasks'].extend(resp_json['data']['tasks'])
                except Exception as e:
                    print(e)
        return result_json
    async def get_copy_done_tasks(self):

        api_endpoint = f"{self.base_url}/api/admin/task/copy/done"




        async with self.session.get(url=api_endpoint) as response:
            text = await response.text()
            print(await response.text())
            resp_json=await response.json()
            return resp_json
    async def close(self):
        await self.session.close()

async def download_risk_file(alist_api:AlistAPI):
    with Session(engine) as session:
        resources = session.exec(select(Resource).where((Resource.has_detect_risk != None) & (Resource.has_detect_risk == True))).all()
        download_file_list = [
            {
                'src_path':f"{i.cloud_storage_path}/{j['file_name']}",
                'dst_pdir_path':f"{i.storage_path}"
            }

            for i in resources
             for j in i.risk_file_handle
             if j['status']=='wait_download'and j.get('skip_download',False)==False
        ]

        resp_json= await alist_api.copy(download_file_list,'夸克网盘','downloads',)
        try :
            resp_task_list=resp_json['data']['tasks']
            task_map={}
            for task in resp_task_list:
                text=task['name']
                download_task_id=task['id']
                # 注意正则表达式字符串前的 r 表示原始字符串，避免反斜杠问题
                regex = r"copy \[.*?\]\((.*?)\) to \[.*?\]\(.*?\)"
                match = re.search(regex, text)
                file_full_name = match.group(1)
                task_map.update({
                    file_full_name:download_task_id,
                })
            for resource in resources:
                for file in resource.risk_file_handle:
                    download_task_id= task_map.get(f"{resource.cloud_storage_path}/{file['file_name']}")
                    if download_task_id is not None  :
                        file['status']='downloading'
                        file['download_task_id']=download_task_id
                print(resource)
                flag_modified(resource, "risk_file_handle")  # 通知 SQLAlchemy 该字段已修改
                session.add(resource)
            try:
                session.commit()
            except Exception as e:
                print(e)
        except Exception as e:
            print(e)

async def upload_risk_file(alist_api:AlistAPI):
    with Session(engine) as session:
        resources = session.exec(
            select(Resource).where((Resource.has_detect_risk != None) & (Resource.has_detect_risk == True))).all()

        upload_file_list = [
            {
                'src_path':  f"{i.storage_path}/{j['file_name']}",
                'dst_pdir_path': f"{i.cloud_storage_path}",
            }

            for i in resources
            for j in i.risk_file_handle
            if j['status'] == 'modified' or j['status'] == 'upload_error'
        ]

        resp_json = await alist_api.copy(upload_file_list, 'downloads','夸克网盘' )
        try:
            resp_task_list = resp_json['data']['tasks']
            task_map = {}
            for task in resp_task_list:
                text = task['name']
                upload_task_id = task['id']
                # 注意正则表达式字符串前的 r 表示原始字符串，避免反斜杠问题
                regex = r"copy \[.*?\]\((.*?)\) to \[.*?\]\(.*?\)"
                match = re.search(regex, text)
                file_full_name = match.group(1)
                task_map.update({
                    file_full_name: upload_task_id,
                })
            for resource in resources:
                for file in resource.risk_file_handle:
                    upload_task_id = task_map.get(f"{resource.cloud_storage_path}/{file['file_name']}")
                    if upload_task_id is not None:
                        file['status'] = 'uploading'
                        file.update({
                            'upload_task_id' : upload_task_id
                        })
                print(resource)
                flag_modified(resource, "risk_file_handle")  # 通知 SQLAlchemy 该字段已修改
                session.add(resource)
            try:
                session.commit()
            except Exception as e:
                print(e)
        except Exception as e:
            print(e)


async def is_finish(alist_api:AlistAPI):
    with Session(engine) as session:
        resources=session.exec(select(Resource).where(Resource.has_detect_risk ==True)).all()
        risk_file_map={
        file['download_task_id']:{
            'risk_file':file,
            'resource':resource
        }
        for resource in resources
            for file in resource.risk_file_handle
                if file['status']=='downloading'
        }

        resp_json= await alist_api.get_copy_done_tasks()
        done_tasks=resp_json['data']
        for task in done_tasks:
            id=task['id']
            risk_file=risk_file_map.get(id)
            if risk_file is None:
                continue
            risk_file['risk_file']['status']='downloaded'
            flag_modified(risk_file['resource'], "risk_file_handle")
            session.add(risk_file['resource'])
        try:
            session.commit()
        except Exception as e:
            print(e)

async def async_upload_status(alist_api:AlistAPI):
    with Session(engine) as session:
        resources = session.exec(select(Resource).where(Resource.has_detect_risk == True)).all()
        risk_file_map = {
            file['upload_task_id']: {
                'risk_file': file,
                'resource': resource
            }
            for resource in resources
            for file in resource.risk_file_handle
            if file['status'] == 'uploading'
        }

        resp_json = await alist_api.get_copy_done_tasks()
        done_tasks = resp_json['data']
        for task in done_tasks:
            id = task['id']
            risk_file = risk_file_map.get(id)
            if risk_file is None:
                continue
            state=task['state']
            if state == 2:
                risk_file['risk_file']['status'] = 'uploaded'
            else:
                risk_file['risk_file']['status'] = 'upload_error'
                risk_file['risk_file'].update({
                    'upload_error_message':task['error']
                })
            flag_modified(risk_file['resource'], "risk_file_handle")
            session.add(risk_file['resource'])
        try:
            session.commit()
        except Exception as e:
            print(e)

async def main():
    alist=AlistAPI()
    await upload_risk_file(alist)
    # await async_upload_status(alist)
    # await download_risk_file(alist)
    # await is_finish(alist)
    await alist.close()
if __name__ == "__main__":

    asyncio.run(main())