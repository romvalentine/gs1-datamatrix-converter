from PIL import Image, ImageEnhance, ImageOps

from config import (
    PHOTO_CONTRAST_VALUES,
    PHOTO_SHARPNESS_VALUES,
    PHOTO_UPSCALE_FACTORS,
)

from core.image_utils import (
    adaptive_threshold_variant,
    add_white_border,
    invert_colors,
    red_channel_inverse,
    blue_channel_inverse,
    enhance_for_red_tape,
    red_blue_difference,
    hsv_like_extraction,
    binarize,
)

from logger import log

from typing import List, Tuple, Dict, Optional


class PhotoMixin:
    """Миксин с методами для фото-режима"""
    
    def upscale(
        self,
        image: Image.Image,
        factor: float,
        resample: Optional[int] = None,
    ) -> Image.Image:
        """Увеличивает изображение с проверкой максимального размера"""
        from config import MAX_UPSCALED_SIZE
        
        if resample is None:
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.LANCZOS
        
        if factor <= 1:
            return image

        width = int(image.width * factor)
        height = int(image.height * factor)

        largest = max(width, height)

        if MAX_UPSCALED_SIZE and largest > MAX_UPSCALED_SIZE:
            correction = MAX_UPSCALED_SIZE / largest
            width = int(width * correction)
            height = int(height * correction)

        result = image.resize(
            (max(1, width), max(1, height)),
            resample,
        )

        log(
            f"photo upscale: "
            f"{image.width}x{image.height} -> "
            f"{result.width}x{result.height}; "
            f"factor={factor}"
        )

        return result
    
    def build_photo_variants(
        self,
        image: Image.Image,
    ) -> List[Tuple[str, Image.Image]]:
        """Создаёт варианты для фото-режима"""
        variants: List[Tuple[str, Image.Image]] = []

        base = image.convert("RGB")

        # Кэшируем апскейленные изображения, чтобы не делать это дважды
        upscaled_cache: Dict[float, Image.Image] = {}

        for scale in PHOTO_UPSCALE_FACTORS:
            # ✅ Кэшируем апскейл
            if scale not in upscaled_cache:
                upscaled_cache[scale] = self.upscale(base, scale)
            
            lanczos_image = upscaled_cache[scale]

            for contrast in PHOTO_CONTRAST_VALUES:
                contrast_image = ImageEnhance.Contrast(
                    lanczos_image
                ).enhance(contrast)

                for sharpness in PHOTO_SHARPNESS_VALUES:
                    sharp_image = ImageEnhance.Sharpness(
                        contrast_image
                    ).enhance(sharpness)

                    sharp_image = add_white_border(sharp_image, border=100)

                    variants.append((
                        f"photo_x{scale}_c{contrast}_s{sharpness}",
                        sharp_image,
                    ))

            gray_image = ImageOps.grayscale(lanczos_image).convert("RGB")
            gray_image = add_white_border(gray_image, border=100)
            variants.append((f"photo_gray_x{scale}", gray_image))

            adaptive_image = adaptive_threshold_variant(
                lanczos_image,
                block_size=15,
                offset=5,
                border=20,
            )
            variants.append((f"photo_adaptive_x{scale}", adaptive_image))

            try:
                bicubic_resample = Image.Resampling.BICUBIC
            except AttributeError:
                bicubic_resample = Image.BICUBIC
            
            # ✅ Кэшируем bicubic апскейл отдельно
            bicubic_key = f"bicubic_{scale}"
            if bicubic_key not in upscaled_cache:
                upscaled_cache[bicubic_key] = self.upscale(base, scale, bicubic_resample)
            
            bicubic_image = upscaled_cache[bicubic_key]
            bicubic_gray = ImageOps.grayscale(bicubic_image).convert("RGB")
            bicubic_gray = add_white_border(bicubic_gray, border=100)
            variants.append((f"photo_bicubic_gray_x{scale}", bicubic_gray))

        # Инвертированные варианты
        for scale in PHOTO_UPSCALE_FACTORS:
            # ✅ Используем кэш
            lanczos_image = upscaled_cache.get(scale)
            if lanczos_image is None:
                lanczos_image = self.upscale(base, scale)
                upscaled_cache[scale] = lanczos_image
            
            inverted = ImageOps.invert(lanczos_image.convert("RGB"))
            inverted_with_border = add_white_border(inverted, border=100)
            variants.append((f"photo_inverted_x{scale}", inverted_with_border))

        # Варианты для красного скотча
        for scale in PHOTO_UPSCALE_FACTORS:
            # ✅ Используем кэш
            lanczos_image = upscaled_cache.get(scale)
            if lanczos_image is None:
                lanczos_image = self.upscale(base, scale)
                upscaled_cache[scale] = lanczos_image

            # Инверсия красного канала
            red_inv = red_channel_inverse(lanczos_image)
            red_inv_border = add_white_border(red_inv, border=100)
            variants.append((f"photo_red_inv_x{scale}", red_inv_border))

            # Инверсия синего канала
            blue_inv = blue_channel_inverse(lanczos_image)
            blue_inv_border = add_white_border(blue_inv, border=100)
            variants.append((f"photo_blue_inv_x{scale}", blue_inv_border))

            # Усиление для красного скотча
            red_tape = enhance_for_red_tape(lanczos_image)
            red_tape_border = add_white_border(red_tape, border=100)
            variants.append((f"photo_red_tape_x{scale}", red_tape_border))

            # Разница R-B
            r_b_diff = red_blue_difference(lanczos_image)
            r_b_border = add_white_border(r_b_diff, border=100)
            variants.append((f"photo_red_blue_diff_x{scale}", r_b_border))

            # HSV экстракция
            hsv = hsv_like_extraction(lanczos_image)
            hsv_border = add_white_border(hsv, border=100)
            variants.append((f"photo_hsv_x{scale}", hsv_border))

            # Инверсия + бинаризация
            inverted = invert_colors(lanczos_image)
            for threshold in [180, 200, 220]:
                bin_inv = binarize(inverted, threshold)
                bin_border = add_white_border(bin_inv, border=100)
                variants.append((
                    f"photo_inv_thr{threshold}_x{scale}",
                    bin_border,
                ))

        log(f"build_photo_variants: created {len(variants)} variants")

        return variants

    def photo_variants(
        self,
        image: Image.Image,
    ) -> List[Tuple[str, Image.Image]]:
        """Возвращает фото-варианты с логированием"""
        variants = self.build_photo_variants(image)
        log(f"photo variants count: {len(variants)}")
        return variants