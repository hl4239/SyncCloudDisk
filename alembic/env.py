# alembic/env.py
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from sqlmodel import SQLModel
from app.domain.models.resource import Resource
# 将项目的根目录添加到 sys.path，以便 Alembic 可以找到你的模块
# 这假设 alembic 目录位于项目根目录下一层
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# --- 从你的应用中导入配置和模型 ---
from app.infrastructure.config import settings  # 导入你的应用配置
  # 导入 SQLModel 基类
# ！！！确保在这里导入所有定义了 table=True 的 SQLModel 模型！！！
# 这样 Alembic 才能检测到它们的变化。

# 如果有其他模型，也在这里导入:
# from app.domain.models.other_model import OtherModel

# -------------------------------------------------

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- 设置 sqlalchemy.url 从你的应用配置 ---
# 这会覆盖 alembic.ini 中的 sqlalchemy.url
config.set_main_option('sqlalchemy.url', settings.database.url)
# -----------------------------------------

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# --- 使用 SQLModel.metadata ---
target_metadata = SQLModel.metadata


# -----------------------------

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # 对于 SQLModel 和 SQLAlchemy 2.0 风格，通常不需要 render_as_batch
        # render_as_batch=True # 对于 SQLite 和某些类型的更改可能需要
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # 使用 engine_from_config 从配置中创建引擎
    # connectable = create_engine(settings.database.url, poolclass=pool.NullPool) # 或者直接使用你的引擎
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),  # 使用 alembic.ini 中的配置节
        prefix="sqlalchemy.",  # sqlalchemy.url 等
        poolclass=pool.NullPool,
        # url=settings.database.url # 也可以直接传递URL，但上面的方式更标准
    )

    # 确保 connectable 使用了我们 settings 中的 URL
    # 如果 engine_from_config 没有正确获取到 URL (例如 alembic.ini 中的 sqlalchemy.url 是空的)
    # 我们可以强制使用我们应用 settings 中的 URL
    if not connectable.url or str(connectable.url) == "placeholder_to_be_overridden_in_env_py":
        from sqlalchemy import create_engine
        print(f"Warning: Overriding Alembic engine URL with application settings: {settings.database.url}")
        connectable = create_engine(settings.database.url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # 对于 SQLModel 和 SQLAlchemy 2.0 风格，通常不需要 render_as_batch
            # render_as_batch=True # 对于 SQLite 和某些类型的更改可能需要
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()