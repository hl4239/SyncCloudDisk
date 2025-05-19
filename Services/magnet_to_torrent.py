import asyncio

from Services.alist_api import AlistAPI
from Services.aria2_api import Aria2API


class MagnetToTorrent:
    def __init__(self,aria2:Aria2API,alist:AlistAPI):
        self.task_list=[]
        self.aria2=aria2
        self.alist=alist
        self.aria2_download_base_path='/vol2/1000/downloads'
        self.alist_base_path='/downloads'
    async def download_magnet(self,url:str,path:str,format_name:str):
        await self.alist.mkdir(self.alist_base_path+path)
        task_id=await self.aria2.download_magnet(magnet_link=url,output_dir=self.aria2_download_base_path+path)
        self.task_list.append({
            'task_id': task_id,
            'path': path,
            'format_name': format_name,
            'status': 'downloading',
        })

    async def query_task(self):
        """
        持续查询任务状态，直到所有指定任务完成

        :param task_id_list: 要查询的任务ID列表
        :return: 包含所有任务结果的列表，每个元素是字典格式 {task_id, status, message}
        """
        completed_result = []
        remaining_tasks = [i['task_id']for i in self.task_list]  # 使用集合提高查找效率
        task_map={
            i['task_id']:i
            for i in self.task_list
        }
        while remaining_tasks:
            # 1. 获取已停止的任务列表
            stopped_json = await self.aria2.tellStopped()
            task_list_ = stopped_json['result']

            # 2. 遍历已停止任务
            for task in task_list_:
                task_id = task['gid']
                status = task['status']

                # 3. 如果是我们关注的任务且未记录过
                if task_id in remaining_tasks:
                    hash = (await self.aria2.tellStatus(task_id))['result']['infoHash']
                    task_map[task_id].update({
                        'hash':hash,
                        'status':status,
                    })
                    remaining_tasks.remove(task_id)  # 从待查询集合中移除

            # 4. 如果还有任务未完成，等待一段时间再查询
            if remaining_tasks:
                await asyncio.sleep(2)  # 避免频繁查询




    async def get_downloaded(self):
        await self.query_task()
        result=[]
        for task in self.task_list:
            if task['status'] == 'complete':
                src_path=self.alist_base_path+task['path']+f'/{task['hash']}.torrent'
                new_name=task['format_name']+'.torrent'
                await self.alist.rename(src_path,new_name)
                new_path=self.alist_base_path+task['path']+f'/{new_name}'
                result.append(new_path)
        return result








