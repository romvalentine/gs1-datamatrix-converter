from PIL import Image

from config import (
    FAST_PAD_FACTORS,
    FAST_UPSCALE_FACTORS,
    MAX_UPSCALED_SIZE,
    MULTI_CROP_SCAN_VALUES,
    MULTI_PAD_FACTORS,
    MULTI_UPSCALE_FACTORS,
    SAFE_PAD_FACTORS,
    SAFE_UPSCALE_FACTORS,
)

from core.image_utils import (
    add_white_border,
    adaptive_threshold_variant,
    binarize,
    contrast_border_variant,
    gray_border_variant,
    gray_threshold_variant,
    resize_if_needed,
    sharpen_image,
    trim_noise_edges,
    invert_colors,
    extract_channel,
    red_channel_inverse,
    green_channel_inverse,
    blue_channel_inverse,
    enhance_for_red_tape,
    enhance_for_green_tape,
    red_blue_difference,
    hsv_like_extraction,
    morphological_open,
    remove_red_tape_noise,
)

from logger import log

import math
from typing import List, Tuple, Set, Optional, Callable, Dict, Any


try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS

except AttributeError:
    RESAMPLE_LANCZOS = Image.LANCZOS


def resize_limited(
    image: Optional[Image.Image],
    scale: float,
) -> Optional[Image.Image]:
    """
    Увеличивает изображение, но не позволяет максимальной стороне
    превысить MAX_UPSCALED_SIZE.
    """
    if image is None:
        return None

    try:
        scale = float(scale)
    except (TypeError, ValueError):
        return image

    if scale <= 1:
        return image

    width = max(
        1,
        int(image.width * scale + 0.5),
    )

    height = max(
        1,
        int(image.height * scale + 0.5),
    )

    largest_side = max(
        width,
        height,
    )

    if largest_side > MAX_UPSCALED_SIZE:
        correction = (
            MAX_UPSCALED_SIZE
            / largest_side
        )

        width = max(
            1,
            int(width * correction + 0.5),
        )

        height = max(
            1,
            int(height * correction + 0.5),
        )

    if (
        width == image.width
        and height == image.height
    ):
        return image

    return image.resize(
        (
            width,
            height,
        ),
        RESAMPLE_LANCZOS,
    )


def rotation_variants(
    image: Image.Image,
) -> List[Tuple[str, Image.Image]]:
    """
    Создаёт варианты изображения с поворотом на 0, 90, 180 и 270 градусов.
    """
    image = image.convert("RGB")

    return [
        (
            "rot0",
            image,
        ),
        (
            "rot90",
            image.rotate(
                90,
                expand=True,
            ),
        ),
        (
            "rot180",
            image.rotate(
                180,
                expand=True,
            ),
        ),
        (
            "rot270",
            image.rotate(
                270,
                expand=True,
            ),
        ),
    ]


def add_variant(
    variants: List[Tuple[str, Image.Image]],
    names: Set[str],
    name: str,
    image: Optional[Image.Image],
) -> None:
    """
    Добавляет вариант, если он корректный и ещё не был добавлен.
    """
    if image is None:
        return

    try:
        if image.width < 2:
            return

        if image.height < 2:
            return

    except Exception:
        return

    if name in names:
        return

    names.add(name)

    variants.append(
        (
            name,
            image,
        )
    )


def add_safe_variant(
    variants: List[Tuple[str, Image.Image]],
    names: Set[str],
    name: str,
    factory: Callable[[], Optional[Image.Image]],
) -> None:
    """
    Безопасно вычисляет и добавляет вариант.

    Если одна из функций обработки изображения завершится ошибкой,
    остальные варианты продолжат создаваться.
    """
    try:
        image = factory()

    except Exception:
        return

    add_variant(
        variants,
        names,
        name,
        image,
    )


def add_scaled_variants(
    variants: List[Tuple[str, Image.Image]],
    names: Set[str],
    name: str,
    image: Optional[Image.Image],
    scales: List[float],
) -> None:
    """
    Добавляет исходный вариант и его масштабированные копии.
    """
    add_variant(
        variants,
        names,
        name,
        image,
    )

    if image is None:
        return

    for scale in scales:
        if scale <= 1:
            continue

        add_safe_variant(
            variants,
            names,
            f"{name}_x{scale}",
            lambda img=image, s=scale: resize_limited(img, s),
        )


def add_memory_variant(
    variants: List[Tuple[str, Image.Image]],
    names: Set[str],
    base_image: Image.Image,
    memory: Any,
    signature: str,
) -> None:
    if memory is None:
        return

    if not signature:
        return

    try:
        preferred = (
            memory.preferred_variant(
                signature
            )
        )

    except Exception:
        return

    if preferred == "contrast_border40":
        add_safe_variant(
            variants,
            names,
            "mem_contrast_border40",
            lambda: contrast_border_variant(
                base_image
            ),
        )

    elif preferred == "gray_border20":
        add_safe_variant(
            variants,
            names,
            "mem_gray_border20",
            lambda: gray_border_variant(
                base_image,
                border=20,
            ),
        )

    elif preferred == "gray_thr200_border20":
        add_safe_variant(
            variants,
            names,
            "mem_gray_thr200_border20",
            lambda: gray_threshold_variant(
                base_image,
                threshold=200,
                border=20,
            ),
        )


def build_fast_variants(
    image: Image.Image,
    memory: Any = None,
    signature: str = None,
) -> List[Tuple[str, Image.Image]]:
    base_image = image.convert("RGB")

    variants: List[Tuple[str, Image.Image]] = []
    names: Set[str] = set()

    add_memory_variant(
        variants,
        names,
        base_image,
        memory,
        signature,
    )

    contrast_image = None

    add_safe_variant(
        variants,
        names,
        "contrast_border40",
        lambda: contrast_border_variant(
            base_image
        ),
    )

    try:
        contrast_image = contrast_border_variant(
            base_image
        )

    except Exception:
        contrast_image = None

    if contrast_image is not None:
        for scale in FAST_UPSCALE_FACTORS:
            add_safe_variant(
                variants,
                names,
                (
                    "contrast_border40_"
                    f"x{scale}"
                ),
                lambda img=contrast_image, s=scale: resize_limited(img, s),
            )

    gray_images: Dict[int, Optional[Image.Image]] = {}

    for padding in FAST_PAD_FACTORS:
        try:
            gray_image = gray_border_variant(
                base_image,
                border=padding,
            )

        except Exception:
            continue

        gray_images[padding] = gray_image

        for scale in FAST_UPSCALE_FACTORS:
            add_safe_variant(
                variants,
                names,
                (
                    f"gray_border{padding}_"
                    f"x{scale}"
                ),
                lambda img=gray_image, s=scale: resize_limited(img, s),
            )

    try:
        threshold_image = gray_threshold_variant(
            base_image,
            threshold=200,
            border=20,
        )

    except Exception:
        threshold_image = None

    if threshold_image is not None:
        for scale in FAST_UPSCALE_FACTORS:
            add_safe_variant(
                variants,
                names,
                (
                    "gray_thr200_border20_"
                    f"x{scale}"
                ),
                lambda img=threshold_image, s=scale: resize_limited(img, s),
            )

    log(f"build_fast_variants: created {len(variants)} variants")

    return variants


def build_safe_variants(
    image: Image.Image,
    memory: Any = None,
    signature: str = None,
) -> List[Tuple[str, Image.Image]]:
    base_image = image.convert("RGB")

    variants: List[Tuple[str, Image.Image]] = []
    names: Set[str] = set()

    add_memory_variant(
        variants,
        names,
        base_image,
        memory,
        signature,
    )

    add_safe_variant(
        variants,
        names,
        "contrast_border40",
        lambda: contrast_border_variant(
            base_image
        ),
    )

    for padding in SAFE_PAD_FACTORS:
        add_safe_variant(
            variants,
            names,
            f"gray_border{padding}",
            lambda p=padding: gray_border_variant(
                base_image,
                border=p,
            ),
        )

    threshold_images: Dict[Tuple[int, int], Optional[Image.Image]] = {}

    for threshold in (
        180,
        200,
        220,
    ):
        for padding in (
            20,
            40,
        ):
            cache_key = (
                threshold,
                padding,
            )

            try:
                threshold_image = gray_threshold_variant(
                    base_image,
                    threshold=threshold,
                    border=padding,
                )

            except Exception:
                continue

            threshold_images[cache_key] = threshold_image

            for scale in SAFE_UPSCALE_FACTORS:
                add_safe_variant(
                    variants,
                    names,
                    (
                        f"gray_thr{threshold}_"
                        f"border{padding}_"
                        f"x{scale}"
                    ),
                    lambda img=threshold_image, s=scale: resize_limited(img, s),
                )

    try:
        sharpened = sharpen_image(
            base_image
        )

    except Exception:
        sharpened = None

    if sharpened is not None:
        for threshold in (
            180,
            200,
            220,
        ):
            try:
                threshold_image = binarize(
                    sharpened,
                    threshold,
                )

            except Exception:
                continue

            for padding in SAFE_PAD_FACTORS:
                try:
                    padded = add_white_border(
                        threshold_image,
                        border=padding,
                    )

                except Exception:
                    continue

                for scale in SAFE_UPSCALE_FACTORS:
                    add_safe_variant(
                        variants,
                        names,
                        (
                            f"safe_thr{threshold}_"
                            f"pad{padding}_"
                            f"x{scale}"
                        ),
                        lambda img=padded, s=scale: resize_limited(img, s),
                    )

    add_safe_variant(
        variants,
        names,
        "adaptive_threshold_border20",
        lambda: adaptive_threshold_variant(
            base_image,
            block_size=15,
            offset=5,
            border=20,
        ),
    )

    add_safe_variant(
        variants,
        names,
        "adaptive_threshold_border40",
        lambda: adaptive_threshold_variant(
            base_image,
            block_size=21,
            offset=8,
            border=40,
        ),
    )

    add_red_tape_processing_variants(
        variants,
        names,
        base_image,
        include_extended=True,
    )

    log(f"build_safe_variants: created {len(variants)} variants")

    return variants


def build_multi_code_variants(
    image: Image.Image,
    memory: Any = None,
    signature: str = None,
) -> List[Tuple[str, Image.Image]]:
    base_image = image.convert("RGB")

    variants: List[Tuple[str, Image.Image]] = []
    names: Set[str] = set()

    add_safe_variant(
        variants,
        names,
        "contrast_border40_x2",
        lambda: resize_limited(
            contrast_border_variant(
                base_image
            ),
            2,
        ),
    )

    for crop_value in MULTI_CROP_SCAN_VALUES:
        working_image = base_image

        if crop_value > 0:
            try:
                working_image = trim_noise_edges(
                    working_image,
                    border_scan=crop_value,
                )

            except Exception:
                working_image = base_image

        for padding in MULTI_PAD_FACTORS:
            padded_image = working_image

            if padding > 0:
                try:
                    padded_image = add_white_border(
                        working_image,
                        border=padding,
                    )

                except Exception:
                    continue

            for scale in MULTI_UPSCALE_FACTORS:
                variant_name = (
                    f"crop{crop_value}_"
                    f"pad{padding}_"
                    f"x{scale}"
                )

                add_safe_variant(
                    variants,
                    names,
                    variant_name,
                    lambda img=padded_image, s=scale: resize_limited(img, s),
                )

    log(f"build_multi_code_variants: created {len(variants)} variants")

    return variants


def add_red_tape_processing_variants(
    variants: List[Tuple[str, Image.Image]],
    names: Set[str],
    base_image: Image.Image,
    include_extended: bool = True,
) -> None:
    """
    Добавляет набор вариантов для изображений с красным, зелёным
    или цветным скотчем.

    Все тяжёлые операции выполняются только один раз.
    """
    cached: Dict[str, Optional[Image.Image]] = {}

    def get_cached(
        key: str,
        factory: Callable[[], Optional[Image.Image]],
    ) -> Optional[Image.Image]:
        if key not in cached:
            try:
                cached[key] = factory()

            except Exception:
                cached[key] = None

        return cached[key]

    inverted = get_cached(
        "inverted",
        lambda: invert_colors(
            base_image
        ),
    )

    red_inverse = get_cached(
        "red_inverse",
        lambda: red_channel_inverse(
            base_image
        ),
    )

    green_inverse = get_cached(
        "green_inverse",
        lambda: green_channel_inverse(
            base_image
        ),
    )

    blue_inverse = get_cached(
        "blue_inverse",
        lambda: blue_channel_inverse(
            base_image
        ),
    )

    red_enhanced = get_cached(
        "red_enhanced",
        lambda: enhance_for_red_tape(
            base_image
        ),
    )

    green_enhanced = get_cached(
        "green_enhanced",
        lambda: enhance_for_green_tape(
            base_image
        ),
    )

    red_blue_diff = get_cached(
        "red_blue_diff",
        lambda: red_blue_difference(
            base_image
        ),
    )

    hsv_extraction = get_cached(
        "hsv_extraction",
        lambda: hsv_like_extraction(
            base_image
        ),
    )

    removed_red_tape = get_cached(
        "removed_red_tape",
        lambda: remove_red_tape_noise(
            base_image
        ),
    )

    add_variant(
        variants,
        names,
        "invert_full",
        inverted,
    )

    add_variant(
        variants,
        names,
        "red_channel_inv",
        red_inverse,
    )

    add_variant(
        variants,
        names,
        "green_channel_inv",
        green_inverse,
    )

    add_variant(
        variants,
        names,
        "blue_channel_inv",
        blue_inverse,
    )

    add_variant(
        variants,
        names,
        "red_tape_enhance",
        red_enhanced,
    )

    add_variant(
        variants,
        names,
        "green_tape_enhance",
        green_enhanced,
    )

    add_variant(
        variants,
        names,
        "red_blue_diff",
        red_blue_diff,
    )

    add_variant(
        variants,
        names,
        "hsv_extraction",
        hsv_extraction,
    )

    add_variant(
        variants,
        names,
        "remove_red_tape",
        removed_red_tape,
    )

    if inverted is not None:
        for threshold in (
            180,
            200,
            220,
        ):
            add_safe_variant(
                variants,
                names,
                f"invert_thr{threshold}",
                lambda t=threshold: binarize(
                    inverted,
                    t,
                ),
            )

    if include_extended:
        add_safe_variant(
            variants,
            names,
            "morph_open",
            lambda: morphological_open(
                base_image
            ),
        )

        if inverted is not None:
            add_safe_variant(
                variants,
                names,
                "invert_morph_open",
                lambda: morphological_open(
                    inverted
                ),
            )

        extended_images = (
            (
                "red_tape_enhance",
                red_enhanced,
            ),
            (
                "red_channel_inv",
                red_inverse,
            ),
            (
                "blue_channel_inv",
                blue_inverse,
            ),
            (
                "red_blue_diff",
                red_blue_diff,
            ),
            (
                "hsv_extraction",
                hsv_extraction,
            ),
            (
                "remove_red_tape",
                removed_red_tape,
            ),
        )

        for name, processed_image in extended_images:
            if processed_image is None:
                continue

            for scale in SAFE_UPSCALE_FACTORS:
                if scale <= 1:
                    continue

                add_safe_variant(
                    variants,
                    names,
                    f"{name}_x{scale}",
                    lambda img=processed_image, s=scale: resize_limited(img, s),
                )


def build_red_tape_variants(
    image: Image.Image,
    memory: Any = None,
    signature: str = None,
) -> List[Tuple[str, Image.Image]]:
    """
    Специальные варианты для изображений с красным скотчем.
    """
    base_image = image.convert("RGB")

    variants: List[Tuple[str, Image.Image]] = []
    names: Set[str] = set()

    add_memory_variant(
        variants,
        names,
        base_image,
        memory,
        signature,
    )

    add_red_tape_processing_variants(
        variants,
        names,
        base_image,
        include_extended=True,
    )

    log(f"build_red_tape_variants: created {len(variants)} variants")

    return variants