from typing import List
from .interface import SearchEngine, BaseProvider
from importlib import import_module
import os

class PanSearchEngine(SearchEngine):
    def __init__(self):
        super().__init__()
        self._load_providers()

    def _load_providers(self):
        """动态加载pansearch/providers目录中的所有Provider"""
        provider_dir = os.path.join(os.path.dirname(__file__), 'providers')
        if not os.path.exists(provider_dir):
            return

        for filename in os.listdir(provider_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                try:
                    module = import_module(f'pansearch.providers.{module_name}')
                    for attr in dir(module):
                        if attr.endswith('Provider') and attr != 'BaseProvider':
                            provider_class = getattr(module, attr)
                            if issubclass(provider_class, BaseProvider):
                                self.add_provider(provider_class())
                except ImportError as e:
                    print(f"Failed to load provider {module_name}: {str(e)}")

    def get_available_providers(self) -> List[str]:
        """获取已加载的Provider名称列表"""
        return [p.__class__.__name__ for p in self.providers]