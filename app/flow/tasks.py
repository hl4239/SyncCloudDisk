# app/flow/tasks.py
import asyncio
import logging

from pydantic import BaseModel
from typing import Dict, Any
from app.core.task_registry import registry
from app.database.models import TVCategory
from app.flow.sync_new_movie_flow import collect_data_hot, combin_to_movies, save_to_database, link_scraping, link_parse
from app.modules.filter.flow import filter_flow
from app.modules.link_parse.schemas import PrepareParseLinks

# 每个任务接受 (params: dict, progress_callback, log_callback) 并返回结果（或抛错）
logger=logging.getLogger(__name__)
class ExampleParams(BaseModel):
    total: int = 10
    interval: float = 1.0
    task_note: str = "demo"

@registry.register(name="example", params_model=ExampleParams)
async def example_long_running_job(params: Dict[str, Any], progress_callback, log_callback):
    # params 已由路由层校验并是 dict（或 Pydantic model dict）
    logger.debug("Example long running job")
    print("Example long running job")
    total = int(params.get("total", 10))
    interval = float(params.get("interval", 1.0))
    name = params.get("task_note", "demo")
    log_callback(f"Example job '{name}' starting: total={total}, interval={interval}")
    for i in range(1, total + 1):
        await asyncio.sleep(interval)
        pct = (i / total) * 100.0
        progress_callback(pct)
        log_callback(f"step {i}/{total}")
        await asyncio.sleep(0)  # 让出事件循环
    logger.debug("Example long running job finished")
    return {"message": f"Example finished {name}", "processed": total}

# 另一个任务示例：数据处理（参数模型不同）
class DataProcParams(BaseModel):
    source: str
    limit: int = 100

@registry.register(name="data_proc", params_model=DataProcParams)
async def data_processing_job(params: Dict[str, Any], progress_callback, log_callback):
    logger.debug("Data processing job")
    movie_data_source_results = await collect_data_hot([TVCategory.CHINA, TVCategory.KOREA], count=1)
    movies = await combin_to_movies(movie_data_source_results)
    await save_to_database(movies)
    scrape_results = await link_scraping(movies, count=3)
    parses_results = await link_parse(
        [PrepareParseLinks(scrape_quark_links=s.quark_links, movie=s.movie) for s in scrape_results])
    filter_results = await filter_flow(parses_results)
    for i in filter_results:
        logger.debug(i.movie)
    progress_callback(100)
    log_callback("Data processing job finished")
    return '666'
