import hashlib

from PIL import (
    Image,
    ImageEnhance,
    ImageFilter,
    ImageOps,
)

from logger import log


try:
    RESAMPLE_LANCZOS = (
        Image.Resampling.LANCZOS
    )

except AttributeError:
    RESAMPLE_LANCZOS = Image.LANCZOS


def image_signature(
    image,
):
    try:
        if image is None:
            return "unknown"

        small = (
            image
            .convert("L")
            .resize(
                (
                    32,
                    32,
                ),
                RESAMPLE_LANCZOS,
            )
        )

        return hashlib.md5(
            small.tobytes()
        ).hexdigest()

    except Exception as error:
        log(
            f"image signature error: "
            f"{error}"
        )

        return "unknown"


def resize_if_needed(
    image,
    max_size,
):
    if image is None:
        return None

    if max_size is None:
        return image

    try:
        max_size = int(max_size)

    except (
        TypeError,
        ValueError,
    ):
        return image

    if max_size <= 0:
        return image

    if (
        image.width <= max_size
        and image.height <= max_size
    ):
        return image

    scale = max_size / max(
        image.width,
        image.height,
    )

    new_size = (
        max(
            1,
            int(image.width * scale),
        ),
        max(
            1,
            int(image.height * scale),
        ),
    )

    log(
        f"resize: "
        f"{image.width}x{image.height} -> "
        f"{new_size[0]}x{new_size[1]}"
    )

    return image.resize(
        new_size,
        RESAMPLE_LANCZOS,
    )


def upscale_image(
    image,
    factor=2,
    max_size=None,
):
    if image is None:
        return None

    try:
        factor = float(factor)

    except (
        TypeError,
        ValueError,
    ):
        factor = 2

    if factor <= 1:
        return image

    width = int(
        image.width * factor
    )

    height = int(
        image.height * factor
    )

    if max_size is not None:
        try:
            max_size = int(max_size)

        except (
            TypeError,
            ValueError,
        ):
            max_size = None

    if (
        max_size is not None
        and max_size > 0
    ):
        largest_side = max(
            width,
            height,
        )

        if largest_side > max_size:
            correction = (
                max_size
                / largest_side
            )

            width = int(
                width * correction
            )

            height = int(
                height * correction
            )

    return image.resize(
        (
            max(1, width),
            max(1, height),
        ),
        RESAMPLE_LANCZOS,
    )


def add_white_border(
    image,
    border=20,
):
    if image is None:
        return None

    try:
        border = max(
            0,
            int(border),
        )

    except (
        TypeError,
        ValueError,
    ):
        border = 0

    if border == 0:
        return image

    return ImageOps.expand(
        image,
        border=border,
        fill="white",
    )


def binarize(
    image,
    threshold,
):
    if image is None:
        return None

    gray = image.convert(
        "L"
    )

    try:
        threshold = int(threshold)

    except (
        TypeError,
        ValueError,
    ):
        threshold = 128

    threshold = max(
        0,
        min(
            255,
            threshold,
        ),
    )

    result = gray.point(
        lambda pixel:
        255
        if pixel > threshold
        else 0
    )

    return result.convert(
        "RGB"
    )


def adaptive_binarize(
    image,
    block_size=15,
    offset=5,
):
    if image is None:
        return None

    gray = ImageOps.grayscale(
        image
    )

    width, height = gray.size

    if width < 1 or height < 1:
        return gray.convert(
            "RGB"
        )

    try:
        block_size = int(block_size)

    except (
        TypeError,
        ValueError,
    ):
        block_size = 15

    try:
        offset = int(offset)

    except (
        TypeError,
        ValueError,
    ):
        offset = 5

    block_size = max(
        3,
        block_size,
    )

    if block_size % 2 == 0:
        block_size += 1

    blurred = gray.filter(
        ImageFilter.GaussianBlur(
            radius=max(
                1,
                block_size // 4,
            )
        )
    )

    source_pixels = gray.load()
    blur_pixels = blurred.load()

    result = Image.new(
        "L",
        (
            width,
            height,
        ),
        255,
    )

    result_pixels = result.load()

    for y in range(height):
        for x in range(width):
            source_value = (
                source_pixels[x, y]
            )

            local_value = (
                blur_pixels[x, y]
            )

            threshold = (
                local_value
                - offset
            )

            result_pixels[x, y] = (
                255
                if source_value > threshold
                else 0
            )

    return result.convert(
        "RGB"
    )


def crop_safe(
    image,
    box,
):
    if image is None:
        return None

    try:
        left, top, right, bottom = box

    except (
        TypeError,
        ValueError,
    ):
        return None

    left = max(
        0,
        int(left),
    )

    top = max(
        0,
        int(top),
    )

    right = min(
        image.width,
        int(right),
    )

    bottom = min(
        image.height,
        int(bottom),
    )

    if right <= left:
        return None

    if bottom <= top:
        return None

    return image.crop(
        (
            left,
            top,
            right,
            bottom,
        )
    )


def trim_noise_edges(
    image,
    bg_threshold=245,
    border_scan=12,
):
    if image is None:
        return None

    image = image.convert(
        "RGB"
    )

    if image.width < 2:
        return image

    if image.height < 2:
        return image

    try:
        bg_threshold = int(
            bg_threshold
        )

    except (
        TypeError,
        ValueError,
    ):
        bg_threshold = 245

    bg_threshold = max(
        0,
        min(
            255,
            bg_threshold,
        ),
    )

    try:
        border_scan = int(
            border_scan
        )

    except (
        TypeError,
        ValueError,
    ):
        border_scan = 12

    border_scan = max(
        0,
        border_scan,
    )

    if border_scan == 0:
        return image

    pixels = image.load()

    left = 0
    top = 0
    right = image.width
    bottom = image.height

    def row_is_white(y):
        for x in range(
            image.width
        ):
            r, g, b = pixels[x, y]

            if (
                r < bg_threshold
                or g < bg_threshold
                or b < bg_threshold
            ):
                return False

        return True

    def column_is_white(x):
        for y in range(
            image.height
        ):
            r, g, b = pixels[x, y]

            if (
                r < bg_threshold
                or g < bg_threshold
                or b < bg_threshold
            ):
                return False

        return True

    max_rows = min(
        border_scan,
        image.height // 2,
    )

    max_columns = min(
        border_scan,
        image.width // 2,
    )

    while (
        top < max_rows
        and row_is_white(top)
    ):
        top += 1

    while (
        bottom > image.height - max_rows
        and row_is_white(bottom - 1)
    ):
        bottom -= 1

    while (
        left < max_columns
        and column_is_white(left)
    ):
        left += 1

    while (
        right > image.width - max_columns
        and column_is_white(right - 1)
    ):
        right -= 1

    if right <= left:
        return image

    if bottom <= top:
        return image

    if (
        left == 0
        and top == 0
        and right == image.width
        and bottom == image.height
    ):
        return image

    log(
        f"trim: "
        f"{image.width}x{image.height} -> "
        f"{right - left}x{bottom - top}"
    )

    return image.crop(
        (
            left,
            top,
            right,
            bottom,
        )
    )


def to_gray_rgb(
    image,
):
    if image is None:
        return None

    return ImageOps.grayscale(
        image
    ).convert("RGB")


def contrast_border_variant(
    image,
):
    gray = to_gray_rgb(
        image
    )

    if gray is None:
        return None

    contrast = ImageEnhance.Contrast(
        gray
    ).enhance(2.0)

    return add_white_border(
        contrast,
        border=40,
    )


def gray_border_variant(
    image,
    border=20,
):
    gray = to_gray_rgb(
        image
    )

    if gray is None:
        return None

    return add_white_border(
        gray,
        border=border,
    )


def gray_threshold_variant(
    image,
    threshold=200,
    border=20,
):
    gray = to_gray_rgb(
        image
    )

    if gray is None:
        return None

    threshold_image = binarize(
        gray,
        threshold,
    )

    return add_white_border(
        threshold_image,
        border=border,
    )


def adaptive_threshold_variant(
    image,
    block_size=15,
    offset=5,
    border=20,
):
    threshold_image = (
        adaptive_binarize(
            image,
            block_size=block_size,
            offset=offset,
        )
    )

    return add_white_border(
        threshold_image,
        border=border,
    )


def sharpen_image(
    image,
):
    gray = to_gray_rgb(
        image
    )

    if gray is None:
        return None

    return gray.filter(
        ImageFilter.SHARPEN
    )


# =============================================================================
# Методы для работы с красным скотчем и цветными помехами
# =============================================================================

def invert_colors(image):
    if image is None:
        return None

    return ImageOps.invert(
        image.convert("RGB")
    )


def extract_channel(image, channel="R"):
    if image is None:
        return None

    image = image.convert(
        "RGB"
    )

    channel = str(
        channel
    ).upper()

    r, g, b = image.split()

    if channel == "R":
        return r.convert("RGB")

    if channel == "G":
        return g.convert("RGB")

    if channel == "B":
        return b.convert("RGB")

    return image


def red_channel_inverse(image):
    if image is None:
        return None

    image = image.convert(
        "RGB"
    )

    r, g, b = image.split()

    r_inverted = ImageOps.invert(
        r
    )

    return Image.merge(
        "RGB",
        (
            r_inverted,
            g,
            b,
        ),
    )


def green_channel_inverse(image):
    if image is None:
        return None

    image = image.convert(
        "RGB"
    )

    r, g, b = image.split()

    g_inverted = ImageOps.invert(
        g
    )

    return Image.merge(
        "RGB",
        (
            r,
            g_inverted,
            b,
        ),
    )


def blue_channel_inverse(image):
    if image is None:
        return None

    image = image.convert(
        "RGB"
    )

    r, g, b = image.split()

    b_inverted = ImageOps.invert(
        b
    )

    return Image.merge(
        "RGB",
        (
            r,
            g,
            b_inverted,
        ),
    )


def enhance_for_red_tape(image):
    if image is None:
        return None

    r, g, b = image.convert(
        "RGB"
    ).split()

    b_enhanced = ImageEnhance.Contrast(
        b
    ).enhance(1.5)

    result = b_enhanced.convert(
        "RGB"
    )

    return binarize(
        result,
        threshold=150,
    )


def enhance_for_green_tape(image):
    if image is None:
        return None

    r, g, b = image.convert(
        "RGB"
    ).split()

    r_enhanced = ImageEnhance.Contrast(
        r
    ).enhance(1.5)

    result = r_enhanced.convert(
        "RGB"
    )

    return binarize(
        result,
        threshold=150,
    )


def channel_difference(image, ch1="R", ch2="B"):
    if image is None:
        return None

    image = image.convert("RGB")
    ch1, ch2 = str(ch1).upper(), str(ch2).upper()
    r, g, b = image.split()

    channels = {"R": r, "G": g, "B": b}
    ch1_img, ch2_img = channels.get(ch1, r), channels.get(ch2, b)

    diff = Image.new("L", image.size)
    diff_pixels = diff.load()
    ch1_pixels, ch2_pixels = ch1_img.load(), ch2_img.load()

    for y in range(image.height):
        for x in range(image.width):
            # ✅ Используйте abs() если нужна полная разница
            diff_pixels[x, y] = abs(ch1_pixels[x, y] - ch2_pixels[x, y])

    return diff.convert("RGB")


def red_blue_difference(image):
    return channel_difference(
        image,
        "R",
        "B",
    )


def hsv_like_extraction(image):
    if image is None:
        return None

    image = image.convert("RGB")
    r, g, b = image.split()

    result = Image.new("L", image.size)
    result_pixels = result.load()
    r_pixels, g_pixels, b_pixels = r.load(), g.load(), b.load()

    for y in range(image.height):
        for x in range(image.width):
            rv, gv, bv = r_pixels[x, y], g_pixels[x, y], b_pixels[x, y]
            max_val, min_val = max(rv, gv, bv), min(rv, gv, bv)

            if max_val == 0:
                saturation = 0
            else:
                saturation = int((max_val - min_val) * 255 / max_val)  # ✅ 


def morphological_open(
    image,
    kernel_size=3,
):
    if image is None:
        return None

    try:
        kernel_size = int(
            kernel_size
        )

    except (
        TypeError,
        ValueError,
    ):
        kernel_size = 3

    kernel_size = max(
        3,
        kernel_size,
    )

    if kernel_size % 2 == 0:
        kernel_size += 1

    image = image.convert(
        "L"
    )

    eroded = image.filter(
        ImageFilter.MinFilter(
            kernel_size
        )
    )

    opened = eroded.filter(
        ImageFilter.MaxFilter(
            kernel_size
        )
    )

    return opened.convert(
        "RGB"
    )


def morphological_close(
    image,
    kernel_size=3,
):
    if image is None:
        return None

    try:
        kernel_size = int(
            kernel_size
        )

    except (
        TypeError,
        ValueError,
    ):
        kernel_size = 3

    kernel_size = max(
        3,
        kernel_size,
    )

    if kernel_size % 2 == 0:
        kernel_size += 1

    image = image.convert(
        "L"
    )

    dilated = image.filter(
        ImageFilter.MaxFilter(
            kernel_size
        )
    )

    closed = dilated.filter(
        ImageFilter.MinFilter(
            kernel_size
        )
    )

    return closed.convert(
        "RGB"
    )


def remove_red_tape_noise(image):
    if image is None:
        return None

    step1 = red_channel_inverse(
        image
    )

    if step1 is None:
        return None

    r, g, b = step1.convert(
        "RGB"
    ).split()

    b_enhanced = ImageEnhance.Contrast(
        b
    ).enhance(1.8)

    result = binarize(
        b_enhanced,
        threshold=140,
    )

    return morphological_open(
        result,
        kernel_size=3,
    )
