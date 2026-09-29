from pathlib import Path

from PIL import Image, ImageSequence

from config import MAX_IMAGE_SIZE

from core.decoder import collect_codes
from core.image_utils import image_signature, resize_if_needed
from core.variants import (
    build_fast_variants,
    build_safe_variants,
    rotation_variants,
)
from core.scanner_border import BorderFixMixin
from core.scanner_photo import PhotoMixin
from core.scanner_crops import CropsMixin

from logger import log

from typing import List, Set, Optional, Callable, Any


def crop_image_manually(image: Image.Image) -> Image.Image:
    """
    Добавляет белый фон вокруг изображения.
    """
    margin = 20
    width, height = image.size
    new_width = width + margin * 2
    new_height = height + margin * 2
    result = Image.new('RGB', (new_width, new_height), 'white')
    result.paste(image, (margin, margin))
    return result


class ImageScanner(BorderFixMixin, PhotoMixin, CropsMixin):
    """Основной класс сканера изображений"""
    
    def __init__(self, memory: Any = None):
        self.memory = memory

    @staticmethod
    def stopped(stop_event: Optional[Any]) -> bool:
        return stop_event is not None and stop_event.is_set()

    @staticmethod
    def merge_codes(
        source: List[Any],
        found: Set[str],
        result: List[str],
    ) -> None:
        for code in source or []:
            if code is None:
                continue
            if code not in found:
                found.add(code)
                result.append(code)

    def scan(
        self,
        image: Image.Image,
        mode: str = "fast",
        prefix: str = "image",
        collect_all: bool = False,
        stop_event: Optional[Any] = None,
        progress_callback: Optional[Callable] = None,
    ) -> List[str]:
        """Основной метод сканирования"""
        if image is None:
            return []

        if self.stopped(stop_event):
            return []

        image = image.convert("RGB")

        if mode == "photo":
            log(f"photo source kept at full size: {image.width}x{image.height}")
        else:
            image = resize_if_needed(image, MAX_IMAGE_SIZE)

        signature = image_signature(image)

        log(f"ImageScanner.scan: mode={mode}, size={image.width}x{image.height}")

        found: Set[str] = set()
        result: List[str] = []

        if mode == "auto":
            mode = "fast"

        if mode == "photo":
            rotations: List[tuple] = [("rot0", image)]
            variants = self.photo_variants(image)

        elif mode == "fast":
            rotations = [("rot0", image)]
            variants = build_fast_variants(
                image,
                memory=self.memory,
                signature=signature,
            )

        else:
            rotations = rotation_variants(image)
            variants = None

        for rotation_name, rotated in rotations:
            if self.stopped(stop_event):
                return result

            if mode in {"fast", "photo"}:
                current_variants = variants
            else:
                current_variants = build_safe_variants(
                    rotated,
                    memory=self.memory,
                    signature=signature,
                )

            for variant_name, variant in current_variants:
                if self.stopped(stop_event):
                    return result

                label = f"{prefix}_{rotation_name}_{variant_name}"

                log(f"variant start: {label} size={variant.width}x{variant.height}")

                if progress_callback:
                    progress_callback(
                        stage="decode",
                        current=0,
                        total=0,
                        label=label,
                    )

                from core.decoder import decode_image
                
                decoded = decode_image(
                    variant,
                    label,
                    stop_event=stop_event,
                )

                if self.stopped(stop_event):
                    return result

                local_found: Set[str] = set()
                local_codes: List[str] = []

                collect_codes(decoded, local_found, local_codes)

                before_count = len(result)
                self.merge_codes(local_codes, found, result)
                added_count = len(result) - before_count

                if added_count > 0:
                    log(
                        f"variant success: {label}; "
                        f"new_codes={added_count}; total_codes={len(result)}"
                    )

                    if self.memory is not None:
                        try:
                            self.memory.record_success(signature, variant_name)
                        except Exception as error:
                            log(f"memory error: {error}")

                    # Возвращаем сразу в fast/photo режиме
                    if result and not collect_all and mode in {"fast", "photo"}:
                        return result

            if result and not collect_all and mode == "safe":
                return result

        return result

    def scan_file(
        self,
        image_path: str,
        mode: str = "fast",
        progress_callback: Optional[Callable] = None,
        stop_event: Optional[Any] = None,
    ) -> List[str]:
        """Сканирует файл изображения"""
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {path}")

        log(f"open image: {path}")

        all_codes: List[str] = []

        with Image.open(path) as source:
            is_gif = path.suffix.lower() == ".gif"

            if is_gif:
                total_frames = getattr(source, "n_frames", 1)

                for frame_index, frame in enumerate(
                    ImageSequence.Iterator(source),
                    start=1,
                ):
                    if self.stopped(stop_event):
                        return []

                    image = frame.convert("RGB")

                    if mode != "photo":
                        image = resize_if_needed(image, MAX_IMAGE_SIZE)

                    if mode == "safe":
                        codes = self.scan_with_border_fix(
                            image,
                            prefix=f"gif{frame_index}",
                            stop_event=stop_event,
                            progress_callback=progress_callback,
                        )
                    elif mode == "manual":
                        manual_crop = crop_image_manually(image)
                        if manual_crop:
                            codes = self.scan(
                                manual_crop,
                                mode="safe",
                                prefix=f"gif{frame_index}_manual",
                                collect_all=True,
                                stop_event=stop_event,
                                progress_callback=progress_callback,
                            )
                        else:
                            codes = []
                    else:
                        codes = self.scan(
                            image,
                            mode=mode,
                            prefix=f"gif{frame_index}",
                            collect_all=True,
                            stop_event=stop_event,
                            progress_callback=progress_callback,
                        )

                    if not codes:
                        codes = self.scan_crops(
                            image,
                            mode=mode,
                            prefix=f"gif{frame_index}",
                            stop_event=stop_event,
                            progress_callback=progress_callback,
                        )

                    self.merge_codes(codes, set(all_codes), all_codes)

                    if progress_callback:
                        progress_callback(
                            stage="frame",
                            current=frame_index,
                            total=total_frames,
                            label=f"GIF frame {frame_index}",
                        )

                log(f"image done: {len(all_codes)} codes")
                return all_codes

            image = source.convert("RGB")

        if self.stopped(stop_event):
            return []

        if mode == "photo":
            codes = self.scan(
                image,
                mode=mode,
                prefix="image",
                collect_all=True,
                stop_event=stop_event,
                progress_callback=progress_callback,
            )

        elif mode == "safe":
            codes = self.scan_with_border_fix(
                image,
                prefix="image",
                stop_event=stop_event,
                progress_callback=progress_callback,
            )

        elif mode == "manual":
            manual_crop = crop_image_manually(image)
            
            if manual_crop:
                log(
                    f"manual crop: {manual_crop.width}x{manual_crop.height}"
                )
                codes = self.scan(
                    manual_crop,
                    mode="safe",
                    prefix="image_manual",
                    collect_all=True,
                    stop_event=stop_event,
                    progress_callback=progress_callback,
                )
            else:
                log("manual crop cancelled")
                codes = []

        else:
            codes = self.scan(
                image,
                mode=mode,
                prefix="image",
                collect_all=(mode not in {"fast", "auto"}),
                stop_event=stop_event,
                progress_callback=progress_callback,
            )

            if not codes:
                codes = self.scan_crops(
                    image,
                    mode=mode,
                    prefix="image",
                    stop_event=stop_event,
                    progress_callback=progress_callback,
                )

        log(f"image done: {len(codes)} codes")
        return codes