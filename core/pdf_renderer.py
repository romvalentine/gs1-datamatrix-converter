import fitz

from PIL import Image

from config import (
    MAX_IMAGE_SIZE,
    TOP_LEFT_DPI,
)

from core.decoder import (
    collect_codes,
    decode_image,
)

from core.image_utils import (
    resize_if_needed,
)

from logger import log


class PdfRendererMixin:
    @staticmethod
    def image_from_pixmap(
        pixmap,
    ):
        return Image.frombytes(
            "RGB",
            (
                pixmap.width,
                pixmap.height,
            ),
            pixmap.samples,
        )

    def render_page(
        self,
        page,
        dpi,
    ):
        log(
            f"render page dpi={dpi}"
        )

        matrix = fitz.Matrix(
            dpi / 72.0,
            dpi / 72.0,
        )

        pixmap = page.get_pixmap(
            matrix=matrix,
            colorspace=fitz.csRGB,
            alpha=False,
        )

        image = self.image_from_pixmap(
            pixmap
        )

        log(
            f"pixmap size: "
            f"{pixmap.width}x"
            f"{pixmap.height}"
        )

        return resize_if_needed(
            image,
            MAX_IMAGE_SIZE,
        )

    def scan_top_left(
        self,
        page,
        stop_event=None,
    ):
        if self.stopped(stop_event):
            return []

        rect = page.rect

        size_pt = (
            20 * 72 / 25.4
        )

        clip = fitz.Rect(
            rect.x0,
            rect.y0,
            rect.x0 + size_pt,
            rect.y0 + size_pt,
        )

        matrix = fitz.Matrix(
            TOP_LEFT_DPI / 72.0,
            TOP_LEFT_DPI / 72.0,
        )

        try:
            pixmap = page.get_pixmap(
                matrix=matrix,
                clip=clip,
                colorspace=fitz.csRGB,
                alpha=False,
            )

            image = self.image_from_pixmap(
                pixmap
            )

            image = resize_if_needed(
                image,
                MAX_IMAGE_SIZE,
            )

            if self.stopped(stop_event):
                return []

            decoded = decode_image(
                image,
                "top-left",
                stop_event=stop_event,
            )

            if self.stopped(stop_event):
                return []

            found = set()
            result = []

            collect_codes(
                decoded,
                found,
                result,
            )

            return result

        except Exception as error:
            log(
                f"top-left error: "
                f"{error}"
            )

            return []