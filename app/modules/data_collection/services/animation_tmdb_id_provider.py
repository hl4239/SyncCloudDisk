import asyncio
import datetime
import logging
from typing import Tuple, List

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import MovieType
from app.modules.data_collection.interfaces.tmdb_id_provider_interface import ITMDBIDProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
import tmdbsimple as tmdb

from app.services.movie_service import movie_service

logger=logging.getLogger(__name__)
class AnimationTMDBIDProvider(ITMDBIDProvider):
    """
    tv版动漫，不包含电影
    """
    @classmethod
    def match_ratio_minbase(cls,a_list, b_list, threshold=0.3):
        a_set, b_set = set(a_list), set(b_list)
        common = a_set & b_set
        base = min(len(a_set), len(b_set)) or 1
        ratio = len(common) / base
        return ratio,ratio >= threshold



    def _search(self,title):
        search = tmdb.Search()
        response = search.tv(
            query=title,
            language='zh-CN',
            include_adult=False
        )
        print(response)
        select_list = [i['id'] for i in response['results'] if title in i['name']]
        print(select_list)
        return select_list
    @classmethod
    def _select_target_season(cls, id_: int, season_numbers: List[int], episode_range:Tuple[int,int], pubdate: datetime.date):
        target_season = None
        for season_number in season_numbers:
            tv_season = tmdb.TV_Seasons(tv_id=id_, season_number=season_number)
            response = tv_season.info()
            start_episode=episode_range[0]
            for episode in response['episodes']:
                if start_episode == episode['episode_number']:
                    date_obj = datetime.datetime.strptime(episode['air_date'], "%Y-%m-%d").date()
                    if date_obj == pubdate:
                        return season_number
                if start_episode < episode['episode_number']:
                    return None
        return None

    from datetime import datetime
    from typing import List, Tuple

    def _select_target_tv(self, ids: List[any], actors: List[str], season: str, episode_range: Tuple[int, int],
                          pubdate: datetime):
        logger.info(f'开始筛选目标剧集 | ids={ids}, season={season}, episode_range={episode_range}, pubdate={pubdate}')

        has_animation_list = []
        for id1 in ids:
            logger.debug(f'正在获取TV信息 | id={id1}')
            tv = tmdb.TV(id1)
            try:
                tv_info = tv.info(language='zh-CN')
            except Exception as e:
                logger.error(f'获取TV信息失败 | id={id1}, error={e}')
                continue

            has_animation = any('动画' in item['name'] for item in tv_info.get('genres', []))
            logger.debug(f'检查是否包含“动画” | id={id1}, has_animation={has_animation}')
            if has_animation:
                has_animation_list.append(tv_info)

        if len(has_animation_list) == 0:
            logger.debug(f'has_animation_list为空 | ids={ids}，返回None')
            return None

        target_tv = None
        if len(has_animation_list) == 1:
            target_tv = has_animation_list[0]
            logger.info(f'仅找到1个含动画的TV | id={target_tv["id"]} name={target_tv.get("name")}')

        # 多个动画类TV时，进一步根据演员匹配筛选
        if len(has_animation_list) > 1:
            logger.info(f'找到多个含动画的TV | 数量={len(has_animation_list)}，开始进行演员匹配')

            actor_match_list = []
            for i in has_animation_list:
                tv = tmdb.TV(i['id'])
                try:
                    response = tv.credits(language='zh')
                except Exception as e:
                    logger.error(f'获取演员信息失败 | id={i["id"]}, error={e}')
                    continue

                tmdb_actors = [c['name'] for c in response.get('cast', [])]
                ratio, is_match = self.match_ratio_minbase(actors, tmdb_actors, 0.2)
                logger.debug(
                    f'演员匹配 | tv_id={i["id"]}, ratio={ratio:.2%}, passed={is_match}, 参与匹配演员={len(tmdb_actors)}')

                if is_match:
                    actor_match_list.append(i)

            if len(actor_match_list) == 0:
                logger.debug(f'actor_match_list为空 | ids={ids}，返回None')
                return None
            if len(actor_match_list) == 1:
                target_tv = actor_match_list[0]
                logger.info(f'演员匹配唯一结果 | id={target_tv["id"]}, name={target_tv.get("name")}')
            if len(actor_match_list) > 1:
                logger.info(f'演员匹配到多个结果，进入季节与时间筛选 | 数量={len(actor_match_list)}')

                final_select_list = []
                for j in actor_match_list:
                    r = self._select_target_season(
                        j['id'],
                        [s['season_number'] for s in j.get('seasons', [])],
                        episode_range,
                        pubdate
                    )
                    if r is not None:
                        final_select_list.append((j['id'], r))
                        logger.debug(f'季节匹配成功 | id={j["id"]}, result={r}')
                    else:
                        logger.debug(f'季节匹配失败 | id={j["id"]}')

                if len(final_select_list) == 0:
                    logger.debug(f'final_select_list为空 | ids={ids}，返回None')
                    return None
                if len(final_select_list) == 1:
                    logger.info(f'最终选中TV | id={final_select_list[0][0]}, season_result={final_select_list[0][1]}')
                    return final_select_list[0]
                if len(final_select_list) > 1:
                    logger.warning(f'最终筛选到多个匹配项，无法唯一确定 | final_select_list={final_select_list}')
                    return None

        if target_tv:
            r = self._select_target_season(
                target_tv['id'],
                [s['season_number'] for s in target_tv.get('seasons', [])],
                episode_range,
                pubdate
            )
            if r is not None:
                logger.info(f'最终确认目标TV | id={target_tv["id"]}, season_result={r}')
                return target_tv['id'], r
            else:
                logger.debug(f'目标TV未通过季节匹配 | id={target_tv["id"]}')
                return None

        logger.warning(f'未能找到合适的目标TV | ids={ids}')
        return None

    async def get_tmdb_id(self, movie_data_source: MovieDataSourceResult) -> Tuple[int, int]:

            title_season=await movie_data_source.title_season
            title=await movie_data_source.title
            season=await movie_data_source.season
            actors=await movie_data_source.actors
            episode_range=movie_service.get_episode_range(await movie_data_source.total_episodes,await movie_data_source.aliases)
            pubdate=await movie_data_source.pubdate
            movie_type=await movie_data_source.movie_type
            is_animation=movie_service.is_animation(await movie_data_source.genres)
            if movie_type == MovieType.TV and is_animation :
                ids = self._search(title)
                r=self._select_target_tv(ids,actors,season,episode_range,pubdate)
                logger.info(f'AnimationTMDBIDProvider匹配{title_season}:{r}')
                return r









            else:
                logger.info(f'{title_season} | {movie_type} | {is_animation}  不符合tv且动画的条件，跳过AnimationTMDBIDProvider')
                return None
animation_tmdb_id_provider = AnimationTMDBIDProvider()
async def main():
    await init_db()
    setup_logging()
    tmdb.API_KEY=settings.TMDB_API_KEY
#     r= animation_tmdb_id_provider._search('仙逆'
#                                            )
#     animation_tmdb_id_provider.select_target_tv(r,['史泽鲲', '张惠霖', '乔苏', '徐雨豪', '刘若班', '胡霖', '孙志诚', '彭敏嘉', '柳知萧', '苏雨山', '李诗萌', '刘思岑', '张恩泽', '周健', '祝敏', '李楠', '常文涛']
# ,None,None)
#     r= animation_tmdb_id_provider._select_target_season(223911,[0,1],(77,178),datetime.date(2025,2,24))
#     print(r)
    from app.modules.data_collection.flow import registry_movie_data_sources

    r=  await registry_movie_data_sources([('36779574',MovieType.TV)])
    print(    await r[0].tmdb_infos
)
if __name__ == '__main__':
    asyncio.run(main())
