import asyncio
import logging
from typing import List

from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import Movie, CloudType
from app.database.movie_repository import movie_repository
from app.modules.publish.clients.tg_bot_client import tg_bot_client
from app.modules.publish.schemas import Publisher
from app.services.movie_service import movie_service


class ShareLinkPublish:
    @staticmethod
    def cloud_type_to_CN(cloud_type:CloudType):
        if cloud_type == CloudType.QUARK:
            return '夸克🔗'
        return '其它🔗'

    async def publish_to_tg(self,movies:List[Movie],retry=3)->bool:
        for movie in movies:
            for i in range(retry):
                pic=movie.pic
                msg=self.general_template(movie)
                r=  await tg_bot_client.send_photo_description(pic,msg)
                if r['ok']:
                    logging.info(f'✅成功向TG发布{movie.title_season}')
                    break
                else:
                    logging.info(f'❌失败向TG发布{movie.title_season}，已重试{i+1}/{retry}次 ,{r}\n pic : \n{pic}\n msg : \n{msg}')



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
))
        return msg


    async def publish(self,movies:List[Movie],publishers:List[Publisher]):
        tasks=[]
        for publisher in publishers:
            if publisher==Publisher.TG:
                tasks.append(self.publish_to_tg(movies))
        await asyncio.gather(*tasks)
share_link_publish_service = ShareLinkPublish()
async def main():
    await init_db()
    setup_logging()
    movies= await movie_repository.find_movies_with_episode_today()
    await share_link_publish_service.publish(movies[4:5],[Publisher.TG])
if __name__ == '__main__':
    asyncio.run(main())
