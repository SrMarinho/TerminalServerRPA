from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from playwright.async_api import Page


@dataclass(frozen=True)
class FieldDef:
    img_prefix: int | None
    ocr_keyword: str | None
    param_key: str
    default: str
    label: str
    offset: int


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
    async def fill(
        self,
        page: Page,
        params: dict,
        log: Callable[[str], None] | None = None,
        cancelar: Callable[[], Awaitable[bool]] | None = None,
    ) -> None: ...
