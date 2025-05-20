import re
from pathlib import Path

import QuarkDisk
from Services.alist_api import AlistAPI


class PushToCloudDisk:
    def __init__(self,alist:AlistAPI,task_list=None):
        self.alist = alist
        self.local_base_path='downloads'
        self.cloud_base_path='夸克网盘'
        self.task_list=[]

    async def push(self,path_list:[],dst_path:str):
        path_list_dict= [
            {
                'src_path':i,
                'dst_pdir_path':dst_path,
            }
            for i in path_list
        ]
        ls_path=f'/{self.cloud_base_path}{dst_path}'
        await self.alist.ls_dir(str(Path(ls_path).parent))
        resp_json= await self.alist.copy(path_list_dict=path_list_dict,base_src=self.local_base_path,base_dst=self.cloud_base_path)
        task_list_ = resp_json['data']['tasks']

        for task in task_list_:
            text = task['name']
            upload_task_id = task['id']
            # 注意正则表达式字符串前的 r 表示原始字符串，避免反斜杠问题
            regex = r"copy \[.*?\]\((.*?)\) to \[.*?\]\(.*?\)"
            match = re.search(regex, text)
            file_full_name = match.group(1)
            self.task_list.append({
                'task_id': upload_task_id,
                # /资源分享/xxx
                'path':file_full_name,
                'status':'uploading'
            })

    async def get_complete(self):
        resp_json = await self.alist.get_copy_done_tasks()
        done_tasks = resp_json['data']

        task_id_map={
            i['task_id']:i
            for i in self.task_list
        }

        for task_ in done_tasks:
            id = task_['id']
            task=task_id_map.get(id)
            if task is not None:
                state = task_['state']
                if state == 2:
                    task.update({
                        'status':'complete'
                    })
                else:
                    task.update({
                        'status':'error',
                        'message':task_['error']
                    })
        return self.task_list
