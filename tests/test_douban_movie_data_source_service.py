import pytest

from app.database.database import init_db, init_db_sync
init_db_sync()
@pytest.mark.asyncio
async def test_get_hot_movies():
    ...

