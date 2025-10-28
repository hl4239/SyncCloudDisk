import asyncio
import logging
from datetime import datetime
from typing import List

import pytz

from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import Movie, CloudType, SystemConfig, PlatformInfo, PublishToPlatformInfo, PlatformEnum
from app.database.movie_repository import movie_repository
from app.modules.publish.clients.tg_client import get_tg_client
from app.services.movie_service import movie_service

logger=logging.getLogger(__name__)
class ShareLinkPublish:
    @staticmethod
    def cloud_type_to_CN(cloud_type:CloudType):
        if cloud_type == CloudType.QUARK:
            return '夸克🔗'
        if cloud_type == CloudType.BAIDU:
            return '百度'
        return '其它🔗'

    async def publish_to_tg(self,platform_info:PlatformInfo,movies:List[Movie],is_delete_old:bool=False,is_ignore_episodes_number:bool=False,):

        for movie in movies:

            publish_infos=next((i for i in movie.publish_to_platform_infos if i.account==platform_info.account),None)
            if not publish_infos:
                publish_infos=   PublishToPlatformInfo(account=platform_info.account, chanel_name=platform_info.channel_name,
                                      platform=platform_info.platform)
                movie.publish_to_platform_infos.append(publish_infos)
            if  is_ignore_episodes_number or publish_infos.episode_number is None or publish_infos.episode_number<movie.get_latest_episode_info().episode_number :
                tg_client = await get_tg_client(platform_info.channel_name)

                pic=movie.pic
                msg=self.general_template(movie)
                r=  await tg_client.send_messages_with_delete_old(pic,msg,is_delete_old=is_delete_old,old_message_id= publish_infos.message_id)
                if r:
                    publish_infos.episode_number=movie.get_latest_episode_info().episode_number
                    publish_infos.success=True
                    publish_infos.message_id=str(r.id)
                publish_infos.publish_time=datetime.now(pytz.timezone('Asia/Shanghai'))



    def general_template(self,movie:Movie):
        for_push_link_maps = {c.share_link: CloudType.get_link_type(c.share_link) for c in movie.cloud_infos if
                              c.share_link}
        description = movie.description
        title = movie.title_season
        year = movie.year
        pic = movie.pic
        msg = (
f"""
🎬 {title} ({year}) {movie_service.generate_episode_progress_str(movie.get_latest_episode_info().episode_number,movie_service.extract_episode_number(movie.total_episodes))}

📝 简介:
{description}

""" + "\n".join(
    [f"{self.cloud_type_to_CN(link_type)} {link}" for link, link_type in for_push_link_maps.items()]
)+f"""

🔖 标签: #{title}
"""
        )
        return msg


    async def publish(self,movies:List[Movie],is_delete_old:bool=False,is_ignore_episodes_number:bool=False,):
        platform_infos=(await SystemConfig.find_one()).platform_infos
        tasks=[]
        for publisher in platform_infos:


            if publisher.platform==PlatformEnum.TG and publisher.enable:
                tasks.append(self.publish_to_tg(publisher,movies,is_delete_old,is_ignore_episodes_number,))
        await asyncio.gather(*tasks)
        await movie_repository.upsert(movies)
        return movies
share_link_publish_service = ShareLinkPublish()
async def main():
    await init_db()
    setup_logging()
    movie=await movie_repository.find_by_douban_id('36455616')
    await share_link_publish_service.publish([movie],is_delete_old=True,is_ignore_episodes_number=True)
    # await share_link_publish_service.publish(movies[4:5],[Publisher.TG])
if __name__ == '__main__':
    asyncio.run(main())
