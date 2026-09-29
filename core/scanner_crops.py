from core.image_utils import crop_safe, resize_if_needed
from config import MAX_IMAGE_SIZE

from typing import List, Tuple, Optional, Any, Set
from PIL import Image


class CropsMixin:
    """Миксин с методами для сканирования кропов"""
    
    def scan_crops(
        self,
        image: Image.Image,
        mode: str = "fast",
        prefix: str = "image",
        stop_event: Optional[Any] = None,
        progress_callback: Optional[Any] = None,
    ) -> List[str]:
        """Сканирует кропы изображения по углам и центру"""
        if image is None:
            return []

        width, height = image.size

        # Размер кропов: 28% от изображения
        crop_width = max(2, int(width * 0.28))
        crop_height = max(2, int(height * 0.28))

        # Позиции кропов: 4 угла + центр
        crops: List[Tuple[str, Tuple[int, int, int, int]]] = [
            ("tl", (0, 0, crop_width, crop_height)),
            ("tr", (width - crop_width, 0, width, crop_height)),
            ("bl", (0, height - crop_height, crop_width, height)),
            ("br", (width - crop_width, height - crop_height, width, height)),
            ("center", (
                int(width * 0.35),
                int(height * 0.35),
                int(width * 0.65),
                int(height * 0.65),
            )),
        ]

        found: Set[str] = set()
        result: List[str] = []

        for crop_name, box in crops:
            if self.stopped(stop_event):
                return result

            crop = crop_safe(image, box)

            if crop is None:
                continue

            crop = resize_if_needed(crop, MAX_IMAGE_SIZE)

            crop_codes = self.scan(
                crop,
                mode=mode,
                prefix=f"{prefix}_{crop_name}",
                collect_all=True,
                stop_event=stop_event,
                progress_callback=progress_callback,
            )

            self.merge_codes(crop_codes, found, result)

        return result