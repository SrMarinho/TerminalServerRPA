from abc import ABC, abstractmethod
from collections.abc import Callable

from playwright.async_api import Page


class BaseReport(ABC):
    @property
    @abstractmethod
    def code(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    def label(self) -> str:
        return f"{self.code} | {self.description}"

    @abstractmethod
    def get_fields(self) -> list[dict]: ...

    @abstractmethod
    async def fill(self, page: Page, params: dict, log: Callable[[str], None] | None = None) -> None: ...
