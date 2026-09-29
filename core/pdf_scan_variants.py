from config import (
    FAST_STABLE_PASSES,
    MULTI_GRID_COLUMNS,
    MULTI_GRID_OVERLAP,
    MULTI_GRID_ROWS,
)

from core.decoder import (
    collect_codes,
    decode_image,
)

from core.variants import (
    build_fast_variants,
    build_multi_code_variants,
    build_safe_variants,
    rotation_variants,
)

from logger import log


class PdfScanVariantsMixin:
    def scan_variants_on_image(
        self,
        image,
        mode,
        prefix,
        signature=None,
        stop_event=None,
        progress_callback=None,
    ):
        if self.stopped(stop_event):
            return []

        if mode == "fast":
            variants = build_fast_variants(
                image,
                memory=(
                    self.image_scanner.memory
                ),
                signature=signature,
            )

            rotations = [
                ("rot0", image)
            ]

            stable_passes = None

        elif mode == "multi":
            variants = build_multi_code_variants(
                image
            )

            rotations = [
                ("rot0", image)
            ]

            stable_passes = 0

        else:
            variants = None

            rotations = rotation_variants(
                image
            )

            stable_passes = None

        found = set()
        result = []

        for rotation_name, rotated in (
            rotations
        ):
            if self.stopped(stop_event):
                return result

            if mode in {
                "fast",
                "multi",
            }:
                current = variants

            else:
                current = build_safe_variants(
                    rotated,
                    memory=(
                        self.image_scanner.memory
                    ),
                    signature=signature,
                )

            for variant_name, variant in (
                current
            ):
                if self.stopped(stop_event):
                    return result

                label = (
                    f"{prefix}_"
                    f"{rotation_name}_"
                    f"{variant_name}"
                )

                if progress_callback:
                    progress_callback(
                        stage="decode",
                        current=0,
                        total=0,
                        label=label,
                    )

                log(
                    f"variant start: "
                    f"{label} "
                    f"size={variant.width}x"
                    f"{variant.height}"
                )

                decoded = decode_image(
                    variant,
                    label,
                    stop_event=stop_event,
                )

                if self.stopped(stop_event):
                    return result

                local_found = set()
                local_codes = []

                collect_codes(
                    decoded,
                    local_found,
                    local_codes,
                )

                before = len(result)

                self.merge_codes(
                    local_codes,
                    found,
                    result,
                )

                added = (
                    len(result)
                    - before
                )

                if added > 0:
                    if stable_passes is not None:
                        stable_passes = 0

                    log(
                        f"variant success: "
                        f"{label}, "
                        f"total_codes="
                        f"{len(result)}"
                    )

                    if (
                        self.image_scanner.memory
                        is not None
                        and signature
                    ):
                        try:
                            self.image_scanner.memory.record_success(
                                signature,
                                variant_name,
                            )

                        except Exception as error:
                            log(
                                f"memory error: "
                                f"{error}"
                            )

                    if (
                        mode == "fast"
                        and len(result) >= 4
                    ):
                        log(
                            f"fast result complete: "
                            f"{len(result)} codes"
                        )

                        return result

                elif (
                    mode == "multi"
                    and result
                ):
                    stable_passes += 1

                    if stable_passes >= (
                        FAST_STABLE_PASSES
                    ):
                        log(
                            f"multi stable result: "
                            f"{len(result)} codes, "
                            f"passes="
                            f"{stable_passes}"
                        )

                        return result

        return result

    def scan_grid_overlap(
        self,
        image,
        prefix,
        stop_event=None,
        progress_callback=None,
    ):
        rows = MULTI_GRID_ROWS
        columns = MULTI_GRID_COLUMNS
        overlap = MULTI_GRID_OVERLAP

        width, height = image.size

        step_x = width / columns
        step_y = height / rows

        tile_width = int(
            step_x * (1 + overlap)
        )

        tile_height = int(
            step_y * (1 + overlap)
        )

        found = set()
        result = []

        for row in range(rows):
            for column in range(columns):
                if self.stopped(stop_event):
                    return result

                left = int(
                    column * step_x
                    - step_x * overlap / 2
                )

                top = int(
                    row * step_y
                    - step_y * overlap / 2
                )

                left = max(
                    0,
                    min(
                        max(
                            0,
                            width - tile_width,
                        ),
                        left,
                    ),
                )

                top = max(
                    0,
                    min(
                        max(
                            0,
                            height - tile_height,
                        ),
                        top,
                    ),
                )

                region = image.crop(
                    (
                        left,
                        top,
                        min(
                            width,
                            left + tile_width,
                        ),
                        min(
                            height,
                            top + tile_height,
                        ),
                    )
                )

                label = (
                    f"{prefix}_"
                    f"r{row + 1}"
                    f"c{column + 1}"
                )

                if progress_callback:
                    progress_callback(
                        stage="decode",
                        current=0,
                        total=0,
                        label=label,
                    )

                decoded = decode_image(
                    region,
                    label,
                    stop_event=stop_event,
                )

                if self.stopped(stop_event):
                    return result

                local_found = set()
                local_codes = []

                collect_codes(
                    decoded,
                    local_found,
                    local_codes,
                )

                self.merge_codes(
                    local_codes,
                    found,
                    result,
                )

        return result