from pathlib import Path

from config import (
    IMAGE_EXTS,
    PDF_EXTS,
)

from core.scanner import ImageScanner
from core.memory import VariantMemory
from core.pdf_scanner import PdfScanner


class FileScanner:
    def __init__(
        self,
        memory: VariantMemory,
    ):
        self.image_scanner = ImageScanner(
            memory
        )

        self.pdf_scanner = PdfScanner(
            self.image_scanner
        )

    def scan(
        self,
        file_path,
        mode="fast",
        progress_callback=None,
        stop_event=None,
        page_range=None,
    ):
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Файл не найден: {path}"
            )

        if (
            stop_event is not None
            and stop_event.is_set()
        ):
            return []

        extension = path.suffix.lower()

        if extension in PDF_EXTS:
            return self.pdf_scanner.scan(
                str(path),
                mode=mode,
                progress_callback=(
                    progress_callback
                ),
                stop_event=stop_event,
                page_range=page_range,
            )

        if extension in IMAGE_EXTS:
            return self.image_scanner.scan_file(
                str(path),
                mode=mode,
                progress_callback=(
                    progress_callback
                ),
                stop_event=stop_event,
            )

        raise ValueError(
            f"Неподдерживаемый формат: "
            f"{extension}"
        )

    def scan_image(self, image, mode="fast"):
        """Сканирует изображение (PIL Image или numpy array)."""
        return self.image_scanner.scan_image(
            image,
            mode=mode,
        )