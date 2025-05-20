import asyncio

from Services.alist_api import AlistAPI
from Services.aria2_api import Aria2API


class DownloadTorrent:
    def __init__(self,aria2:Aria2API):
        self.task_list=[]
        self.aria2=aria2
        self.aria2_download_base_path='/vol2/1000/downloads'
    async def download_torrent(self,url:str,path:str,name:str):

        resp_json=await self.aria2.add_download_torrent(url=url,path=self.aria2_download_base_path+path,file=name)
        task_id=resp_json['result']
        self.task_list.append({
            'task_id': task_id,
            'path': path,
            'name': name,
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
            print(task_list_)
            # 2. 遍历已停止任务
            for task in task_list_:
                task_id = task['gid']
                status = task['status']

                # 3. 如果是我们关注的任务且未记录过
                if task_id in remaining_tasks:

                    task_map[task_id].update({

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
                path=task['path']
                name=task['name']
                result.append(f'{path}/{name}')
        return result
async def main():
    down=DownloadTorrent(aria2=Aria2API())
    await down.download_torrent(url='https://www.3bt0.com/prod/api/v1/down?app_id=83768d9ad4&identity=23734adac0301bccdcb107c4aa21f96c&lx=1&id=1747671706728375',path='/资源分享',name='nihao111.torrent')
    await down.download_torrent(
        url='https://www.3bt0.com/prod/api/v1/down?app_id=83768d9ad4&identity=23734adac0301bccdcb107c4aa21f96c&lx=1&id=1747671706728375',
        path='/资源分享', name='nihao222.torrent')
    result = await down.get_downloaded()
    print(result)
if __name__ == '__main__':
    asyncio.run(main())

