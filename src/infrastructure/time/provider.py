from abc import ABC, abstractmethod
from datetime import datetime


class TimeProvider(ABC):
    @abstractmethod
    def now(self) -> datetime:
        pass


class SystemTimeProvider(TimeProvider):
    def now(self) -> datetime:
        from datetime import timezone

        return datetime.now(timezone.utc)
