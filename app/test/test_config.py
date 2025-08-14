from app.infrastructure.config import settings


def test_load_config():
    print(settings.cloud_base_path)
