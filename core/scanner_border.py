import numpy as np
import cv2
from PIL import Image, ImageOps, ImageEnhance, ImageDraw

from logger import log
from core.decoder import decode_image, collect_codes
from core.image_utils import add_white_border

from typing import List, Tuple, Optional, Any, Dict


class BorderFixMixin:
    """Миксин с методами для восстановления контура DataMatrix"""
    
    def _find_l_pattern(
        self,
        img_array: np.ndarray,
        width: int,
        height: int,
        dark: bool = True,
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Ищет L-паттерн (левая и нижняя линии).
        """
        left_edge = None
        bottom_edge = None
        
        if dark:
            for col in range(min(30, width)):
                if np.mean(img_array[:, col]) < 100:
                    left_edge = col
                    break
            
            for row in range(height - 1, max(0, height - 30), -1):
                if np.mean(img_array[row, :]) < 100:
                    bottom_edge = row
                    break
        else:
            for col in range(min(30, width)):
                if np.mean(img_array[:, col]) > 150:
                    left_edge = col
                    break
            
            for row in range(height - 1, max(0, height - 30), -1):
                if np.mean(img_array[row, :]) > 150:
                    bottom_edge = row
                    break
        
        return left_edge, bottom_edge
    
    def _add_white_border_and_l_pattern(
        self,
        image: Image.Image,
    ) -> Image.Image:
        """
        Добавляет белую тихую зону и восстанавливает отсутствующие
        стороны рамки DataMatrix.
        """
        gray = np.array(image.convert("L"))
        height, width = gray.shape
        black_mask = gray < 128
        black_pixels = np.where(black_mask)

        # Если чёрных пикселей нет — только создаём тихую белую зону.
        if len(black_pixels[0]) == 0:
            margin = max(20, int(max(width, height) * 0.20))
            result = Image.new(
                "RGB",
                (width + margin * 2, height + margin * 2),
                "white",
            )
            result.paste(image.convert("RGB"), (margin, margin))
            return result

        # Предполагаемые границы символа.
        top = int(np.min(black_pixels[0]))
        bottom = int(np.max(black_pixels[0]))
        left = int(np.min(black_pixels[1]))
        right = int(np.max(black_pixels[1]))

        code_width = max(1, right - left + 1)
        code_height = max(1, bottom - top + 1)

        # Белая тихая зона со всех четырёх сторон.
        margin = max(30, int(max(code_width, code_height) * 0.25))

        result = Image.new(
            "RGB",
            (width + margin * 2, height + margin * 2),
            "white",
        )
        result.paste(image.convert("RGB"), (margin, margin))

        result_gray = np.array(result.convert("L"))
        result_black = result_gray < 128

        x0 = margin + left
        x1 = margin + right
        y0 = margin + top
        y1 = margin + bottom

        # Толщина области, в которой ищем линию рамки.
        edge_thickness = max(2, min(6, min(code_width, code_height) // 18))

        def classify_horizontal_edge(y, x_start, x_end):
            best_coverage = 0.0
            best_line = y

            for yy in range(
                max(0, y - edge_thickness),
                min(result_black.shape[0], y + edge_thickness + 1),
            ):
                line = result_black[yy, x_start:x_end + 1]
                coverage = float(np.mean(line))

                if coverage > best_coverage:
                    best_coverage = coverage
                    best_line = yy

            if best_coverage >= 0.70:
                return "solid", best_line, best_coverage

            if best_coverage >= 0.12:
                return "dotted", best_line, best_coverage

            return "missing", y, best_coverage

        def classify_vertical_edge(x, y_start, y_end):
            best_coverage = 0.0
            best_line = x

            for xx in range(
                max(0, x - edge_thickness),
                min(result_black.shape[1], x + edge_thickness + 1),
            ):
                line = result_black[y_start:y_end + 1, xx]
                coverage = float(np.mean(line))

                if coverage > best_coverage:
                    best_coverage = coverage
                    best_line = xx

            if best_coverage >= 0.70:
                return "solid", best_line, best_coverage

            if best_coverage >= 0.12:
                return "dotted", best_line, best_coverage

            return "missing", x, best_coverage

        # Определяем состояние всех четырёх сторон.
        top_type, top_y, top_score = classify_horizontal_edge(y0, x0, x1)
        bottom_type, bottom_y, bottom_score = classify_horizontal_edge(y1, x0, x1)
        left_type, left_x, left_score = classify_vertical_edge(x0, y0, y1)
        right_type, right_x, right_score = classify_vertical_edge(x1, y0, y1)

        log(
            "DataMatrix borders: "
            f"top={top_type}({top_score:.2f}), "
            f"right={right_type}({right_score:.2f}), "
            f"bottom={bottom_type}({bottom_score:.2f}), "
            f"left={left_type}({left_score:.2f})"
        )

        # Размер одного условного модуля для восстановления пунктиров.
        module_size = max(2, min(code_width, code_height) // 24)
        line_width = max(1, module_size // 2)

        draw = ImageDraw.Draw(result)

        def draw_solid_horizontal(y):
            draw.line([(x0, y), (x1, y)], fill="black", width=line_width)

        def draw_solid_vertical(x):
            draw.line([(x, y0), (x, y1)], fill="black", width=line_width)

        def draw_dotted_horizontal(y):
            x = x0
            while x <= x1:
                end_x = min(x + module_size - 1, x1)
                draw.line(
                    [(x, y), (end_x, y)],
                    fill="black",
                    width=line_width,
                )
                x += module_size * 2

        def draw_dotted_vertical(x):
            y = y0
            while y <= y1:
                end_y = min(y + module_size - 1, y1)
                draw.line(
                    [(x, y), (x, end_y)],
                    fill="black",
                    width=line_width,
                )
                y += module_size * 2

        # В нормальной ориентации DataMatrix:
        # top/right — пунктир; bottom/left — сплошная рамка.
        if top_type == "missing":
            log("Border repair: добавляю верхнюю пунктирную сторону")
            draw_dotted_horizontal(y0)

        if right_type == "missing":
            log("Border repair: добавляю правую пунктирную сторону")
            draw_dotted_vertical(x1)

        if bottom_type == "missing":
            log("Border repair: добавляю нижнюю сплошную сторону")
            draw_solid_horizontal(y1)

        if left_type == "missing":
            log("Border repair: добавляю левую сплошную сторону")
            draw_solid_vertical(x0)

        return result
    
    def _scan_with_border_fix(
        self,
        image: Image.Image,
        prefix: str = "border_fix",
        stop_event: Optional[Any] = None,
    ) -> List[str]:
        """
        Сканирование с автоматическим восстановлением контура DataMatrix.
        """
        log(f"border fix start: size={image.width}x{image.height}")
        
        img_gray = image.convert('L')
        img_array = np.array(img_gray)
        height, width = img_array.shape
        
        # 1. Ищем L-паттерн
        left_edge, bottom_edge = self._find_l_pattern(
            img_array, width, height, dark=True,
        )
        
        if left_edge is None or bottom_edge is None:
            log("L-pattern not found (dark), trying inverted...")
            img_array_inv = 255 - img_array
            left_edge, bottom_edge = self._find_l_pattern(
                img_array_inv, width, height, dark=False,
            )
            img_array = img_array_inv
        
        log(f"L-pattern: left={left_edge}, bottom={bottom_edge}")
        
        # 2. Если нашли L-паттерн, обрезаем
        if left_edge is not None and bottom_edge is not None:
            code_size = min(width - left_edge, bottom_edge + 1)
            margin = int(code_size * 0.3)
            
            crop_left = max(0, left_edge - margin)
            crop_top = max(0, bottom_edge - code_size - margin)
            crop_right = min(width, left_edge + code_size + margin)
            crop_bottom = min(height, bottom_edge + margin)
            
            cropped = img_array[crop_top:crop_bottom, crop_left:crop_right]
            log(f"border fix: cropped to {cropped.shape[1]}x{cropped.shape[0]}")
            
            base_image = Image.fromarray(cropped, mode='L').convert('RGB')
            
            # 3. Добавляем белый фон и L-паттерн
            enhanced_image = self._add_white_border_and_l_pattern(base_image)
            
            # 4. Пробуем декодировать
            result = self._try_many_variants(
                enhanced_image, prefix, stop_event,
            )
            
            if result:
                return result

            # 4a. Если к одной из сторон DataMatrix прилегает чёрный фон,
            # создаём варианты с отбеливанием этого фона.
            gray_base = np.array(base_image.convert("L"))
            base_height, base_width = gray_base.shape

            edge_width = min(2, base_width)
            edge_height = min(2, base_height)

            edge_black_ratio = {
                "left": float(np.mean(gray_base[:, :edge_width] < 128)),
                "right": float(np.mean(gray_base[:, -edge_width:] < 128)),
                "top": float(np.mean(gray_base[:edge_height, :] < 128)),
                "bottom": float(np.mean(gray_base[-edge_height:, :] < 128)),
            }

            log(
                "edge black ratio: "
                f"left={edge_black_ratio['left']:.2f}, "
                f"right={edge_black_ratio['right']:.2f}, "
                f"top={edge_black_ratio['top']:.2f}, "
                f"bottom={edge_black_ratio['bottom']:.2f}"
            )

            max_x_cleanup = min(16, max(1, base_width // 3))
            max_y_cleanup = min(16, max(1, base_height // 3))

            for side, black_ratio in edge_black_ratio.items():
                if black_ratio < 0.70:
                    continue

                max_cleanup = (
                    max_x_cleanup
                    if side in {"left", "right"}
                    else max_y_cleanup
                )

                log(
                    f"black background detected at {side}: "
                    f"ratio={black_ratio:.2f}; "
                    f"trying cleanup 1..{max_cleanup}px"
                )

                for cut_size in range(1, max_cleanup + 1):
                    if self.stopped(stop_event):
                        return []

                    cleaned = base_image.copy()
                    draw = ImageDraw.Draw(cleaned)

                    if side == "left":
                        draw.rectangle(
                            [(0, 0), (cut_size - 1, base_height - 1)],
                            fill="white",
                        )

                    elif side == "right":
                        draw.rectangle(
                            [
                                (base_width - cut_size, 0),
                                (base_width - 1, base_height - 1),
                            ],
                            fill="white",
                        )

                    elif side == "top":
                        draw.rectangle(
                            [(0, 0), (base_width - 1, cut_size - 1)],
                            fill="white",
                        )

                    elif side == "bottom":
                        draw.rectangle(
                            [
                                (0, base_height - cut_size),
                                (base_width - 1, base_height - 1),
                            ],
                            fill="white",
                        )

                    log(
                        f"edge cleanup variant: side={side}; "
                        f"white_size={cut_size}px"
                    )

                    cleaned_enhanced = (
                        self._add_white_border_and_l_pattern(cleaned)
                    )

                    result = self._try_many_variants(
                        cleaned_enhanced,
                        f"{prefix}_{side}_clean{cut_size}",
                        stop_event,
                    )

                    if result:
                        log(
                            f"edge cleanup succeeded: "
                            f"side={side}; cut_size={cut_size}px"
                        )
                        return result
            
            # 5. Если не получилось — пробуем без enhancement
            log("enhanced decode failed, trying without enhancement...")
            result = self._try_many_variants(
                base_image, f"{prefix}_no_enhance", stop_event,
            )
            
            if result:
                return result
        
        log("border fix: no L-pattern found or decode failed")
        return []
    
    def _try_many_variants(
        self,
        image: Image.Image,
        prefix: str = "variant",
        stop_event: Optional[Any] = None,
    ) -> List[str]:
        """
        Пробует множество вариантов обработки изображения.
        """
        variants: List[Tuple[str, Image.Image]] = []
        
        # 1. Оригинальное
        variants.append(("image_orig", image))
        
        # 2. Инверсия
        variants.append(("image_inv", ImageOps.invert(image.convert('RGB')).convert('RGB')))
        
        # 3. Бинаризация
        img_gray = image.convert('L')
        for threshold in [128, 150]:
            binary = img_gray.point(lambda x: 255 if x > threshold else 0, '1')
            variants.append((f"image_binary{threshold}", binary.convert('RGB')))
        
        # 4. Повороты + safe threshold
        img_array = np.array(img_gray)
        
        # ✅ Исправление: проверка LANCZOS
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
        
        for angle in [90, 180, 270]:
            rotated = np.rot90(img_array, k=angle//90)
            
            for threshold in [200, 220]:
                binary = (rotated < threshold).astype(np.uint8) * 255
                
                # x2
                img = Image.fromarray(binary, mode='L').convert('RGB')
                img_x2 = img.resize((img.width * 2, img.height * 2), resample)
                variants.append((f"image_rot{angle}_safe_thr{threshold}_pad0_x2", img_x2))
                
                # С padding
                for pad in [20, 40]:
                    padded = np.pad(binary, pad, mode='constant', constant_values=255)
                    img = Image.fromarray(padded, mode='L').convert('RGB')
                    variants.append((f"image_rot{angle}_safe_thr{threshold}_pad{pad}", img))
        
        # 5. Повороты + adaptive threshold
        for angle in [90, 180, 270]:
            rotated = np.rot90(img_array, k=angle//90)
            
            for block_size in [21, 15]:
                # ✅ Исправление: проверка размера изображения
                if rotated.shape[0] < block_size or rotated.shape[1] < block_size:
                    continue
                    
                adaptive = cv2.adaptiveThreshold(
                    rotated, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, block_size, 10
                )
                for pad in [40, 20]:
                    padded = np.pad(adaptive, pad, mode='constant', constant_values=255)
                    img = Image.fromarray(padded, mode='L').convert('RGB')
                    variants.append((f"image_rot{angle}_adaptive_thr{block_size}_border{pad}", img))
        
        # Пробуем все варианты
        for name, variant_img in variants:
            if stop_event and stop_event.is_set():
                return []
            
            log(f"variant start: {name} size={variant_img.width}x{variant_img.height}")
            
            decoded = decode_image(variant_img, name, stop_event=stop_event)
            
            local_found = set()
            local_codes = []
            collect_codes(decoded, local_found, local_codes)
            
            if local_codes:
                log(f"SUCCESS: {name}; codes={len(local_codes)}")
                return local_codes
        
        log("all variants failed")
        return []
    
    def scan_with_border_fix(
        self,
        image: Image.Image,
        prefix: str = "border_fix",
        stop_event: Optional[Any] = None,
        progress_callback: Optional[Any] = None,
    ) -> List[str]:
        if image is None:
            return []

        if self.stopped(stop_event):
            return []

        log(f"scan_with_border_fix: size={image.width}x{image.height}")

        result = self._scan_with_border_fix(
            image, prefix=prefix, stop_event=stop_event,
        )

        if result:
            log(f"border fix succeeded: {len(result)} codes")
            return result

        log(f"border fix failed, falling back to safe mode")

        return self.scan(
            image, mode="safe", prefix=prefix,
            collect_all=True, stop_event=stop_event,
            progress_callback=progress_callback,
        )