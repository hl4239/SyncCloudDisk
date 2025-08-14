import pytest

from app.infrastructure.containers import Container
from log import init_logging

init_logging()


@pytest.mark.asyncio
async def test__traverse():
    container = Container()
    cloud_disk_service = container.cloud_disk_service()
    cloud_disk_service.init_cloud_api()
    f = cloud_disk_service._traverse('/', 'quark-4295', create_missing=True)
    print(f)


@pytest.mark.asyncio
async def test_ls_dir():
    container = Container()
    cloud_disk_service = container.cloud_disk_service()
    cloud_disk_service.init_cloud_api()
    f1 = await cloud_disk_service.ls_dir('/资源分享/热门-国产剧', 'quark-4295', refresh=True)
    f = await cloud_disk_service.ls_dir('/资源分享', 'quark-4295', refresh=False)

    print(f, f1)


@pytest.mark.asyncio
async def test_fetch_dir_info():
    container = Container()
    cloud_disk_service = container.cloud_disk_service()
    cloud_disk_service.init_cloud_api()
    f1 = await cloud_disk_service.fetch_dir_info('/资源分享/热门-国产剧1', 'quark-4295')

    print(f1)


@pytest.mark.asyncio
async def test_mkdir():
    container = Container()
    cloud_disk_service = container.cloud_disk_service()
    cloud_disk_service.init_cloud_api()
    f1 = await cloud_disk_service.mkdir('/资源分享/热门-国产', 'quark-4295')

    print(f1)


@pytest.mark.asyncio
async def test_save_from_share():
    container = Container()
    cloud_share_service = container.cloud_share_service()

    cloud_disk_service = container.cloud_disk_service()
    f = await cloud_share_service.get_parse_info('https://pan.quark.cn/s/c787f7f6c951')

    cloud_disk_service.init_cloud_api()
    f1 = await cloud_disk_service.save_from_share(share_parse_info=f, share_files=f.root.children, path='/你好啊',
                                                  name_type='quark-7505')

    print(f1)

@pytest.mark.asyncio
async def test_create_share_link():
    container = Container()
    cloud_disk_service = container.cloud_disk_service()
    cloud_disk_service.init_cloud_api()
    cloud_file=await cloud_disk_service.get_dir_info('/你好啊', name_type='quark-7505')

    f1 = await cloud_disk_service.create_share_link(cloud_files=[cloud_file],name_type='quark-7505')

    print(f1)
