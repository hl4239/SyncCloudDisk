from app.infrastructure.cloud_storage.cloud_api_abc import CloudAPIABC
from app.infrastructure.cloud_storage.providers.quark_cloud_api import QuarkCloudAPI
from app.infrastructure.config import CloudAPIType, CloudAPIConfig


class CloudAPIFactory:
    _instances: dict[str, CloudAPIABC] = {}

    @classmethod
    def _make_key(cls, disk_config: CloudAPIConfig) -> str:
        return f'{disk_config.type.value}-{disk_config.name}'

    @classmethod
    def get_by_key(cls, key: str) -> CloudAPIABC:
        if key not in cls._instances:
            raise KeyError(f"No cloud disk instance with key: {key}")
        return cls._instances[key]

    @classmethod
    async def init_cloud_api(cls, disk_config: CloudAPIConfig) :
        """
        如果已初始化则返回现有的api实例，否则创建
        :param disk_config:
        :return:
        """
        key = cls._make_key(disk_config)

        if key not in cls._instances:
            if disk_config.type == CloudAPIType.QUARK:
                instance = QuarkCloudAPI(disk_config)
                await instance.init_session()
            # 添加其他类型支持
            else:
                raise ValueError(f"Unsupported disk type: {disk_config.type}")

            cls._instances[key] = instance

        return cls._instances[key],key

    @classmethod
    async def close_all(cls):
        for api in cls._instances.values():
            await api.close()
        cls._instances.clear()
