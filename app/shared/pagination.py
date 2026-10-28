from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    page: int
    limit: int
    total: int

    @property
    def total_pages(self) -> int:
        return ceil(self.total / self.limit)
