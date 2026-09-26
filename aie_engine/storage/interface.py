from abc import ABC, abstractmethod
from datetime import timedelta
from pathlib import Path
class ObjectStorage(ABC):
 @abstractmethod
 def upload(self, key: str, file: Path) -> None: ...
 @abstractmethod
 def download(self, key: str, destination: Path) -> None: ...
 @abstractmethod
 def signed_url(self, key: str, expires_in: timedelta) -> str: ...
