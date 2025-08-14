import os
import logging.config
import yaml
from pathlib import Path


def init_logging():
    # 获取当前文件所在目录的绝对路径
    current_dir = Path(__file__).parent.absolute()

    # 创建logs目录（如果不存在），确保在当前文件所在目录下
    logs_dir = current_dir
    logs_dir.mkdir(exist_ok=True)  # 自动创建目录

    # 加载配置，确保log.yaml也在当前文件所在目录下
    config_path = current_dir / "log.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 确保日志文件的路径是绝对路径
    if 'handlers' in config:
        for handler in config['handlers'].values():
            if 'filename' in handler:
                # 将相对路径转换为绝对路径
                if not Path(handler['filename']).is_absolute():
                    handler['filename'] = str(logs_dir / handler['filename'])

    logging.config.dictConfig(config)


if __name__ == "__main__":
    init_logging()
    logger = logging.getLogger(__name__)
    logger.info("日志系统已初始化，文件将保存在 logs/ 目录下")