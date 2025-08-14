from typing import List
from sqlmodel import Session, select, delete  # delete 用于按条件批量删除

from app.domain.models.resource import Resource, TvCategory  # 根据项目路径导入模型
from app.infrastructure.persistence.repositories.auto_sync_repository import AutoSyncRepository


class ResourceRepository(AutoSyncRepository):
    """
    Resource 实体的仓储类，封装批量操作。
    注意：该类不负责 session 的 commit / rollback / close，由上层调用方或服务层管理事务。
    """

    def __init__(self, session: Session):
        self.session = session  # SQLModel 的 Session 实例

    def add_many(self, resources: List[Resource]) -> List[Resource]:
        """
        批量添加资源对象。
        不在此提交事务；如果需要立即获取插入后的 ID，调用方可执行 session.flush()。
        """
        if not resources:
            return []
        self.session.add_all(resources)
        return resources

    def get_by_ids(self, resource_ids: List[int]) -> List[Resource]:
        """
        根据 ID 列表查询资源对象。
        输入为空则返回空列表；去重以避免重复 ID 查询。
        """
        if not resource_ids:
            return []
        unique_ids = list(set(resource_ids))
        statement = select(Resource).where(Resource.id.in_(unique_ids))
        results = self.session.exec(statement).all()
        return list(results)

    def get_resources_by_titles(self, titles: list[str]) -> list[Resource]:
        """
        根据标题列表查询资源（使用 SQLAlchemy 原始接口）。
        """
        return self.session.query(Resource).filter(Resource.title.in_(titles)).all()

    def get_by_titles(self, titles: List[str]) -> List[Resource]:
        """
        根据标题列表精确匹配查询资源。
        注意大小写敏感性取决于数据库的 collation 设置。
        """
        if not titles:
            return []
        unique_titles = list(set(titles))
        statement = select(Resource).where(Resource.title.in_(unique_titles))
        results = self.session.exec(statement).all()
        return list(results)

    def get_all(self) -> List[Resource]:
        """
        查询所有资源。
        """
        statement = select(Resource)
        results = self.session.exec(statement).all()
        return list(results)

    def get_by_category(self, category: TvCategory, count: int) -> List[Resource]:
        """
        查询某个分类下，按元数据更新时间倒序排列的前 count 个资源。
        """
        statement = (
            select(Resource)
            .where(Resource.tv_category == category)
            .order_by(Resource.last_metadata_update_time.desc())
            .limit(count)
        )
        results = self.session.exec(statement).all()
        return list(results)

    def get_by_title_contains(self, title_substring: str) -> List[Resource]:
        """
        模糊查询标题中包含指定子字符串的资源。
        """
        if not title_substring:
            return []
        statement = select(Resource).where(Resource.title.contains(title_substring))
        results = self.session.exec(statement).all()
        return list(results)



    def delete_by_ids(self, resource_ids: List[int]) -> int:
        """
        根据 ID 批量删除资源，使用 SQL DELETE 语句，效率较高。
        不触发 ORM 事件（如 before_delete）。
        返回实际删除的行数。
        不提交事务，调用方需执行 commit。
        """
        if not resource_ids:
            return 0

        unique_ids = list(set(resource_ids))
        statement = delete(Resource).where(Resource.id.in_(unique_ids))
        result = self.session.exec(statement)
        return result.rowcount

    def delete_many(self, resources: List[Resource]) -> int:
        """
        批量删除已加载的资源对象。
        要求资源对象存在 id。
        不提交事务。
        返回实际删除数量（已标记为删除的对象数量）。
        """
        if not resources:
            return 0
        count = 0
        for resource in resources:
            if resource.id is not None:
                self.session.delete(resource)
                count += 1
        return count

