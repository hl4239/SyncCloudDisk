import pytest

from core.logging_config import setup_logging
from modules.publish.clients.tg_client import get_tg_client


@pytest.mark.asyncio
async def test_tg_client():
    setup_logging()
    channel = '@pancloudshare'
    tg_client = await get_tg_client(channel)
    await tg_client.search_messages(search='#围猎', limit=1)
    await tg_client.send_message('Nihao')