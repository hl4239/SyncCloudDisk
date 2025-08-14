from app.utils import SimpleMutablePydanticDict


class AutoSyncRepository:
    """自动同步仓库基类"""

    def __init__(self, session):
        self.session = session

    def auto_sync_before_commit(self, instances):
        """在提交前自动同步所有Pydantic字段"""
        if not isinstance(instances, (list, tuple)):
            instances = [instances]

        for instance in instances:
            self._sync_pydantic_fields(instance)

    def _sync_pydantic_fields(self, instance):
        """同步实例中的所有Pydantic字段"""
        # 获取实例的所有字段
        for column in instance.__table__.columns:
            # 检查字段是否是我们的Pydantic字段
            if hasattr(column.type, 'model_class'):
                field_value = getattr(instance, column.name)
                if isinstance(field_value, SimpleMutablePydanticDict):
                    # 执行同步
                    field_value.sync_from_model()
                    print(f"已同步字段 {column.name}")

    def update_many(self, instances):
        """
        不存在则追加，存在则更新，不必被session跟踪
        :param instances:
        :return:
        """

        # 自动同步
        self.auto_sync_before_commit(instances)

        # 执行更新
        for instance in instances:
            self.session.merge(instance)

        return instances

    def update(self, instance):
        """更新单个实例"""
        return self.update_many([instance])[0]

    def save(self, instance):
        """
        增加一个新的
        :param instance:
        :return:
        """
        self.auto_sync_before_commit(instance)
        self.session.add(instance)
        return instance