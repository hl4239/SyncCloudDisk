import asyncio
import datetime

from sqlalchemy import inspect
from sqlalchemy.util import await_only
from sqlmodel import Session, select

import settings
from CrawlerResource.crawler_douban import CrawlerDouban
from database import engine
from models.resource import Resource, ResourceCategory


class AsyncDouban:

    async def _crawler_resource(self,tv_type: ResourceCategory):
        base_path = settings.STORAGE_BASE_PATH
        resources = []
        async with  CrawlerDouban() as crawler:
            resp_json = await crawler.get_hot_tv(tv_type)
            print(resp_json)
            try:
                sub_items = resp_json['subject_collection_items']
                for item in sub_items:
                    title = f'{item["title"]}({item['year']})'
                    subtitle = item["card_subtitle"]
                    description = item['comment']
                    pic_path = item['pic']['large']
                    storage_path = f'{base_path}/{tv_type.value}/{title}'
                    total_episode = item['episodes_info']

                    resource = Resource(title=title, subtitle=subtitle, description=description, image_path=pic_path,
                                        category=tv_type, storage_path=storage_path, total_episodes=total_episode,douban_last_async=datetime.datetime.now(),cloud_storage_path=storage_path)
                    resources.append(resource)
                return resources
            except Exception as e:
                print(e)
                return None



    async def _update_to_datebase(self,update_list: [Resource | None]):
        check_title = [i.title for i in update_list]
        with Session(engine) as session:
            statement = select(Resource).where(Resource.title.in_(check_title))
            exsiting_resources = session.exec(statement).all()
            existing_resources_map: dict[str, Resource] = {
                resource.title: resource for resource in exsiting_resources
            }
            mapper = inspect(Resource).mapper
            resources_to_add = []
            resources_to_update = []
            for resource in update_list:
                exist_resource = existing_resources_map.get(resource.title)
                if exist_resource:
                    # for column in mapper.columns:
                    #     if column.primary_key:
                    #         continue
                    #     field_name = column.key
                    #
                    #     if field_name =='total_episodes':
                    #         need_update=self._is_need_update(resource.total_episodes,exist_resource.total_episodes)
                    #         exist_resource.need_update = need_update
                    #     if hasattr(exist_resource, field_name):
                    #         new_value = getattr(resource, field_name)
                    #         setattr(exist_resource, field_name, new_value)
                    exist_resource.title=resource.title
                    exist_resource.subtitle=resource.subtitle
                    exist_resource.description=resource.description
                    exist_resource.image_path=resource.image_path
                    exist_resource.category=resource.category
                    exist_resource.storage_path=resource.storage_path
                    exist_resource.cloud_storage_path=resource.storage_path
                    exist_resource.douban_last_async=resource.douban_last_async
                    if exist_resource.total_episodes!=resource.total_episodes and resource.total_episodes!="":
                        exist_resource.total_episodes = resource.total_episodes
                        exist_resource.douban_last_episode_update=datetime.datetime.now()
                    session.add(exist_resource)
                    resources_to_update.append(exist_resource.title)
                else:
                    resource.douban_last_episode_update=datetime.datetime.now()
                    session.add(resource)
                    resources_to_add.append(resource.title)
            try:
                # 提交事务
                session.commit()
                print(f"操作完成。插入 {len(resources_to_add)} 条记录, 更新 {len(resources_to_update)} 条记录。")
                if resources_to_add:
                    print(f"插入的标题: {resources_to_add}")
                if resources_to_update:
                    print(f"更新的标题: {resources_to_update}")


            except Exception as e:
                session.rollback()
                print(f"处理资源时发生未知错误: {e}")
                raise  # 重新抛出，或者根据需要处理

    async def update_resource(self):
        update_list = []
        for tv_type in ResourceCategory:
            update_resources = await self. _crawler_resource(tv_type)
            if update_resources is None:
                print(f'抓取{tv_type}失败')
                continue
            update_list.extend(update_resources)
        await self._update_to_datebase(update_list)
async def main():
    async_douban=AsyncDouban()
    await async_douban.update_resource()
if __name__ == "__main__":
    asyncio.run(main())