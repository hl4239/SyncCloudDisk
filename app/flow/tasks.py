# app/flow/tasks.py
import asyncio
import logging

from pydantic import BaseModel, Field

from app.core.logging_config import setup_logging
from app.core.task_registry import registry
from app.database.database import init_db

# 每个任务接受 (params: dict, progress_callback, log_callback) 并返回结果（或抛错）
logger=logging.getLogger(__name__)
class ExampleParams(BaseModel):
    total: int = Field(default=10,description='总数')
    interval: float = 1.0
    task_note: str = "demo"

@registry.register(name="example", params_model=ExampleParams)
async def example_long_running_job(params: ExampleParams, progress_callback, log_callback):
    # params 已由路由层校验并是 dict（或 Pydantic model dict）
    logger.debug("Example long running job")
    print("Example long running job")
    total = params.total
    interval = params.interval
    name = params.task_note
    log_callback(f"Example job '{name}' starting: total={total}, interval={interval}")
    for i in range(1, total + 1):
        await asyncio.sleep(interval)
        pct = (i / total) * 100.0
        progress_callback(pct)
        log_callback(f"step {i}/{total}")
        await asyncio.sleep(0)  # 让出事件循环
    logger.debug("Example long running job finished")
    return {"message": f"Example finished {name}", "processed": total}


async def main():
    await init_db()
    setup_logging()
if __name__ == '__main__':
    asyncio.run(main())
