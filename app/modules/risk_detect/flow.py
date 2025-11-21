import asyncio
import logging
from typing import List

from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import Movie, CloudShareLink
from app.database.movie_repository import movie_repository
from app.modules.link_parse.schemas import PrepareParseLinks
from app.modules.link_parse.services.link_parser import link_parser
from app.modules.risk_detect.schemas import RiskDetectResult
from app.utils.async_iterator import AsyncCachedIterator
from app.utils.lazy_load import lazy

logger=logging.getLogger(__name__)
async def detect_risk_share(movies:List[Movie])->List[RiskDetectResult]:
    result_risks=[]
    p = await link_parser.parse_links([PrepareParseLinks(
        links=[CloudShareLink(url=cloud_info.share_link)for cloud_info in (movie.cloud_infos or []) if  cloud_info and cloud_info.share_link and cloud_info.is_risk_share==False ],
        scrape_quark_links=lazy(lambda: AsyncCachedIterator([])),
        scrape_baidu_links=lazy(lambda: AsyncCachedIterator([])),
        movie=movie)for movie in movies])

    for r in p:
        valid_shares = []
        async for i in r.baidu_parses:
            valid_shares.append(i.link.url)
        async for i in r.quark_parses:  # ⚠️ 注意：原来写的 p.quark_parses 应该是 r.quark_parses
            valid_shares.append(i.link.url)

        # 生成映射表 {share_link: cloud_info对象}
        all_cloud_info_share_link_maps = {
            i.share_link: i
            for i in (r.movie.cloud_infos or [])
            if i and i.share_link
        }

        all_shares = set(all_cloud_info_share_link_maps.keys())
        valid_set = set(valid_shares)

        # ❌ 筛选出无效的 share_link
        invalid_share_links = list(all_shares - valid_set)

        # ❌ 从映射表中取出对应的 cloud_info 对象
        invalid_cloud_infos = [
            all_cloud_info_share_link_maps[link]
            for link in invalid_share_links
        ]
        for i in invalid_cloud_infos:
            i.is_risk_share = True
            i.risk_detected_count+=1
        result_risks.append(RiskDetectResult(movie=r.movie, risk_cloud_infos=invalid_cloud_infos))
    return result_risks
async def main():
    setup_logging()
    await    init_db()
    movies=await movie_repository.find_movies_with_episode_today()
    r= await    detect_risk_share(movies)
    logger.info({
        i.movie.title_season:[
            j.share_link for j in i.risk_cloud_infos
        ]

    for i in r})


if __name__ == '__main__':
    asyncio.run(main())








