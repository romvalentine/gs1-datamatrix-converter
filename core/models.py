from dataclasses import dataclass
from typing import Optional


@dataclass
class ScanResult:
    """
    Результат обработки одного файла.
    """
    file_path: str
    codes_count: int
    elapsed: float
    mode: str
    status: str
    error: str = ""
    pages: Optional[int] = None


@dataclass
class CodeResult:
    """
    Подробная информация об одном коде.
    """
    code: str
    file_path: str
    page_number: Optional[int] = None
    source: str = ""
    variant: str = ""
    elapsed: float = 0.0