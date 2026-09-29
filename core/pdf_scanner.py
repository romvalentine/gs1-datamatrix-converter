import time

import fitz

from config import (
    PDF_DPI,
    RETRY_DPI,
    RETRY_ENABLED,
)

from core.image_utils import (
    image_signature,
)

from core.pdf_renderer import (
    PdfRendererMixin,
)

from core.pdf_scan_helpers import (
    PdfScanHelpersMixin,
)

from core.pdf_scan_variants import (
    PdfScanVariantsMixin,
)

from logger import format_seconds, log


class PdfScanner(
    PdfRendererMixin,
    PdfScanHelpersMixin,
    PdfScanVariantsMixin,
):
    def __init__(
        self,
        image_scanner,
    ):
        self.image_scanner = image_scanner

    def scan(
        self,
        pdf_path,
        mode="fast",
        progress_callback=None,
        stop_event=None,
        page_range=None,  # ← Новый параметр: (from_page, to_page) или None
    ):
        all_codes = []

        log(
            f"open PDF: {pdf_path}"
        )

        with fitz.open(pdf_path) as document:
            total_pages = len(
                document
            )

            # Определяем диапазон страниц
            if page_range:
                from_page, to_page = page_range
                # Преобразуем в 0-based индексы
                start_index = max(0, from_page - 1)
                end_index = min(total_pages, to_page)
                pages_to_scan = range(start_index, end_index)
                log(
                    f"page range: {from_page}-{to_page} "
                    f"(индексы {start_index}-{end_index-1})"
                )
            else:
                pages_to_scan = range(total_pages)

            log(
                f"pages: {total_pages}"
            )

            for page_index in pages_to_scan:
                if self.stopped(stop_event):
                    break

                page_number = (
                    page_index + 1
                )

                started_at = (
                    time.perf_counter()
                )

                try:
                    page = document[
                        page_index
                    ]

                    log(
                        f"page {page_number}/"
                        f"{total_pages}: start"
                    )

                    if progress_callback:
                        progress_callback(
                            stage="page",
                            current=page_number,
                            total=total_pages,
                            label=(
                                f"Страница "
                                f"{page_number}/"
                                f"{total_pages}"
                            ),
                        )

                    page_codes = (
                        self.scan_page(
                            page,
                            mode=mode,
                            stop_event=stop_event,
                            progress_callback=(
                                progress_callback
                            ),
                        )
                    )

                    elapsed = (
                        time.perf_counter()
                        - started_at
                    )

                    if page_codes:
                        all_codes.extend(
                            page_codes
                        )

                        log(
                            f"page {page_number}: "
                            f"found "
                            f"{len(page_codes)} codes"
                        )

                    elif not self.stopped(
                        stop_event
                    ):
                        all_codes.append(
                            None
                        )

                    log(
                        f"page {page_number}/"
                        f"{total_pages} done in "
                        f"{format_seconds(elapsed)}"
                    )

                except Exception as error:
                    log(
                        f"page {page_number}: "
                        f"ERROR {error}"
                    )

                    if not self.stopped(
                        stop_event
                    ):
                        all_codes.append(
                            None
                        )

                if progress_callback:
                    progress_callback(
                        stage="page_done",
                        current=page_number,
                        total=total_pages,
                        label=(
                            f"Страница "
                            f"{page_number} завершена"
                        ),
                    )

        return all_codes

    def scan_page(
        self,
        page,
        mode="fast",
        stop_event=None,
        progress_callback=None,
    ):
        if self.stopped(stop_event):
            return []

        image = self.render_page(
            page,
            PDF_DPI,
        )

        if mode == "auto":
            mode = "multi"

        if mode == "fast":
            return self.scan_fast_page(
                page,
                image,
                stop_event=stop_event,
                progress_callback=(
                    progress_callback
                ),
            )

        if mode == "multi":
            return self.scan_multi_page(
                page,
                image,
                stop_event=stop_event,
                progress_callback=(
                    progress_callback
                ),
            )

        return self.scan_safe_page(
            page,
            image,
            stop_event=stop_event,
            progress_callback=(
                progress_callback
            ),
        )

    def scan_fast_page(
        self,
        page,
        image,
        stop_event=None,
        progress_callback=None,
    ):
        codes = self.scan_full_image(
            image,
            "full",
            stop_event=stop_event,
        )

        if codes:
            return codes

        if self.stopped(stop_event):
            return []

        signature = image_signature(
            image
        )

        variants = (
            self.scan_variants_on_image(
                image,
                mode="fast",
                prefix="fast",
                signature=signature,
                stop_event=stop_event,
                progress_callback=(
                    progress_callback
                ),
            )
        )

        if variants:
            return variants

        if self.stopped(stop_event):
            return []

        return self.scan_top_left(
            page,
            stop_event=stop_event,
        )

    def scan_multi_page(
        self,
        page,
        image,
        stop_event=None,
        progress_callback=None,
    ):
        found = set()
        result = []

        signature = image_signature(
            image
        )

        first = (
            self.scan_variants_on_image(
                image,
                mode="fast",
                prefix="pdf",
                signature=signature,
                stop_event=stop_event,
                progress_callback=(
                    progress_callback
                ),
            )
        )

        self.merge_codes(
            first,
            found,
            result,
        )

        log(
            f"multi first pass found: "
            f"{len(result)}"
        )

        if self.stopped(stop_event):
            return result

        if len(result) < 4:
            extended = (
                self.scan_variants_on_image(
                    image,
                    mode="multi",
                    prefix="pdf_multi",
                    signature=signature,
                    stop_event=stop_event,
                    progress_callback=(
                        progress_callback
                    ),
                )
            )

            self.merge_codes(
                extended,
                found,
                result,
            )

            if self.stopped(stop_event):
                return result

        if len(result) < 2:
            grid = self.scan_grid_overlap(
                image,
                prefix="pdf_grid",
                stop_event=stop_event,
                progress_callback=(
                    progress_callback
                ),
            )

            self.merge_codes(
                grid,
                found,
                result,
            )

            if self.stopped(stop_event):
                return result

        if result or not RETRY_ENABLED:
            return result

        retry_image = self.render_page(
            page,
            RETRY_DPI,
        )

        if self.stopped(stop_event):
            return result

        retry_signature = image_signature(
            retry_image
        )

        retry = (
            self.scan_variants_on_image(
                retry_image,
                mode="multi",
                prefix="retry_multi",
                signature=retry_signature,
                stop_event=stop_event,
                progress_callback=(
                    progress_callback
                ),
            )
        )

        self.merge_codes(
            retry,
            found,
            result,
        )

        if self.stopped(stop_event):
            return result

        if result:
            return result

        retry_grid = self.scan_grid_overlap(
            retry_image,
            prefix="retry_grid",
            stop_event=stop_event,
            progress_callback=(
                progress_callback
            ),
        )

        self.merge_codes(
            retry_grid,
            found,
            result,
        )

        if self.stopped(stop_event):
            return result

        if result:
            return result

        top_left = self.scan_top_left(
            page,
            stop_event=stop_event,
        )

        self.merge_codes(
            top_left,
            found,
            result,
        )

        return result

    def scan_safe_page(
        self,
        page,
        image,
        stop_event=None,
        progress_callback=None,
    ):
        found = set()
        result = []

        signature = image_signature(
            image
        )

        fast = (
            self.scan_variants_on_image(
                image,
                mode="fast",
                prefix="safe_fast",
                signature=signature,
                stop_event=stop_event,
                progress_callback=(
                    progress_callback
                ),
            )
        )

        self.merge_codes(
            fast,
            found,
            result,
        )

        if result:
            return result

        if self.stopped(stop_event):
            return result

        grid = self.scan_grid_overlap(
            image,
            prefix="safe_grid",
            stop_event=stop_event,
            progress_callback=(
                progress_callback
            ),
        )

        self.merge_codes(
            grid,
            found,
            result,
        )

        if result:
            return result

        if self.stopped(stop_event):
            return result

        safe = self.scan_variants_on_image(
            image,
            mode="safe",
            prefix="safe",
            signature=signature,
            stop_event=stop_event,
            progress_callback=(
                progress_callback
            ),
        )

        self.merge_codes(
            safe,
            found,
            result,
        )

        if result:
            return result

        if self.stopped(stop_event):
            return result

        retry_image = self.render_page(
            page,
            RETRY_DPI,
        )

        if self.stopped(stop_event):
            return result

        retry = self.scan_variants_on_image(
            retry_image,
            mode="safe",
            prefix="safe_retry",
            signature=None,
            stop_event=stop_event,
            progress_callback=(
                progress_callback
            ),
        )

        self.merge_codes(
            retry,
            found,
            result,
        )

        if result:
            return result

        if self.stopped(stop_event):
            return result

        top_left = self.scan_top_left(
            page,
            stop_event=stop_event,
        )

        self.merge_codes(
            top_left,
            found,
            result,
        )

        return result