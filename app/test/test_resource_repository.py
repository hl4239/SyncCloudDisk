import asyncio

import pytest

from app.domain.models.resource import Resource, Account
from app.infrastructure.containers import Container, container


class TestResourceRepository:
    repo=Container().resource_repo()
    def test_add_many(self):

        self.repo.add_many([Resource(title='你好')])
        self.repo.session.commit()
        assert True

    def test_upsert_many(self):
        container = Container()
        repo = container.resource_repo()
        repo.upsert_many([Resource(title='你好',description='dsaddassa')])
        repo.session.commit()
        assert True
    @pytest.mark.asyncio
    async def test_upsert_1(self):
        repo=container.resource_repo()
        resource  =repo.get_by_titles(['藏海传(2025)'])[0]
        async def t(account:Account):

            account.last_sync_share_links=[]
            print(account)
        tasks=[]

        # tasks=[t(account) for account in resource.cloud_disk_info.accounts ]
        # tasks=[t(resource.cloud_disk_info.accounts[0])]
        tasks.append(t(resource.cloud_disk_info.accounts[0]))
        tasks.append(t(resource.cloud_disk_info.accounts[1]))
        await asyncio.gather(*tasks)

        repo.update_many([resource])
        repo.session.commit()

    def test_get_by_ids(self):
        assert False

    def test_get_resources_by_titles(self):
        assert False

    def test_get_by_titles(self):
        assert False

    def test_get_all(self):
        assert False

    def test_get_by_category(self):
        assert False

    def test_get_by_title_contains(self):
        assert False

    def test_update_many(self):
        assert False

    def test_delete_by_ids(self):
        assert False

    def test_delete_many(self):
        assert False




