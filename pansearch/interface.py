from abc import ABC, abstractmethod
from typing import List, Dict

class SearchResult:
    def __init__(self, title: str, url: str, size: str,time, source: str):
        self.title = title
        self.url = url
        self.size = size
        self.time=time
        self.source = source
        
    def __str__(self):
        return f"{self.title} | {self.url} | {self.time} | {self.source}"

class BaseProvider(ABC):
    @abstractmethod
    def search(self, keyword: str) -> List[SearchResult]:
        pass

class SearchEngine:
    def __init__(self):
        self.providers: List[BaseProvider] = []
        
    def add_provider(self, provider: BaseProvider):
        self.providers.append(provider)
        
    def search(self, keyword: str) -> List[SearchResult]:
        results = []
        for provider in self.providers:
            try:
                results.extend(provider.search(keyword))
            except Exception as e:
                print(f"Error in {provider.__class__.__name__}: {str(e)}")
        return results