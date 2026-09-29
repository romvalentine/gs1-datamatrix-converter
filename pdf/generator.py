import io
import time

from pathlib import Path
from datetime import datetime
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from config import PAGE_SETTINGS

from logger import format_seconds, log


def mm_to_points(
    value_mm,
):
    return (
        float(value_mm)
        * 72.0
        / 25.4
    )


def is_valid_code(
    code_data,
):
    if code_data is None:
        return False

    if isinstance(
        code_data,
        str,
    ):
        return bool(
            code_data.strip()
        )

    return True


def build_datamatrix_image(
    code_data,
):
    try:
        from pystrich.datamatrix import (
            DataMatrixData,
            DataMatrixEncoder,
        )

        from pystrich.datamatrix.data import (
            FNC1,
        )

    except ImportError as error:
        raise ImportError(
            "Библиотека pyStrich "
            "не установлена.\n"
            "Выполните:\n"
            "python -m pip install pyStrich"
        ) from error

    text = str(
        code_data
    ).strip()

    if text.startswith(
        "{FNC1}"
    ):
        text = text[
            len("{FNC1}"):
        ]

    if not text:
        raise ValueError(
            "Пустое значение DataMatrix"
        )

    payload = DataMatrixData(
        FNC1,
        text,
        encoding="ascii",
    )

    encoder = DataMatrixEncoder(
        payload
    )

    return encoder.get_pilimage()


def draw_error_page(
    pdf,
    text,
    margin,
):
    pdf.setFont(
        "Helvetica",
        7,
    )

    pdf.drawString(
        margin,
        margin,
        text,
    )


def make_result(
    output_path,
    total_count,
    success_count,
    errors=None,
    fatal_error=None,
    successful_codes=None,
):
    errors = list(
        errors or []
    )

    successful_codes = list(
        successful_codes or []
    )

    failed_count = max(
        0,
        total_count
        - success_count,
    )

    is_complete = (
        total_count > 0
        and success_count == total_count
        and failed_count == 0
        and not errors
        and fatal_error is None
    )

    return {
        "output_path": (
            str(output_path)
            if output_path is not None
            else None
        ),
        "total_count": total_count,
        "success_count": success_count,
        "failed_count": failed_count,
        "successful_codes": (
            successful_codes
        ),
        "errors": errors,
        "fatal_error": fatal_error,
        "is_complete": is_complete,
        "has_errors": not is_complete,
    }


def resolve_page_settings(
    page_width_mm=None,
    page_height_mm=None,
    margin_mm=None,
    code_size_mm=None,
    horizontal_shift_mm=None,
    vertical_shift_mm=None,
):
    if page_width_mm is None:
        page_width_mm = (
            PAGE_SETTINGS.width_mm
        )

    if page_height_mm is None:
        page_height_mm = (
            PAGE_SETTINGS.height_mm
        )

    if margin_mm is None:
        margin_mm = (
            PAGE_SETTINGS.margin_mm
        )

    if code_size_mm is None:
        code_size_mm = (
            PAGE_SETTINGS.code_size_mm
        )

    if horizontal_shift_mm is None:
        horizontal_shift_mm = (
            PAGE_SETTINGS
            .horizontal_shift_mm
        )

    if vertical_shift_mm is None:
        vertical_shift_mm = (
            PAGE_SETTINGS
            .vertical_shift_mm
        )

    settings = {
        "page_width_mm": float(
            page_width_mm
        ),
        "page_height_mm": float(
            page_height_mm
        ),
        "margin_mm": float(
            margin_mm
        ),
        "code_size_mm": float(
            code_size_mm
        ),
        "horizontal_shift_mm": float(
            horizontal_shift_mm
        ),
        "vertical_shift_mm": float(
            vertical_shift_mm
        ),
    }

    if (
        settings["page_width_mm"]
        <= 0
    ):
        raise ValueError(
            "Ширина страницы "
            "должна быть больше нуля"
        )

    if (
        settings["page_height_mm"]
        <= 0
    ):
        raise ValueError(
            "Высота страницы "
            "должна быть больше нуля"
        )

    if settings["margin_mm"] < 0:
        raise ValueError(
            "Поле не может быть "
            "отрицательным"
        )

    if (
        settings["code_size_mm"]
        <= 0
    ):
        raise ValueError(
            "Размер кода должен быть "
            "больше нуля"
        )

    return settings


def generate_pdf_with_codes(
    codes,
    output_path,
    page_width_mm=None,
    page_height_mm=None,
    margin_mm=None,
    code_size_mm=None,
    horizontal_shift_mm=None,
    vertical_shift_mm=None,
    progress_callback=None,
):
    output_path = Path(
        output_path
    )

    # Если это файл manual_codes.pdf в корне проекта,
    # перенаправляем в отдельную папку с уникальным именем.
    if output_path.name == "manual_codes.pdf":
        manual_dir = Path(__file__).parent.parent / "manual_codes"
        manual_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime(
            "%Y-%m-%d_%H%M%S"
        )

        output_path = (
            manual_dir / f"manual_codes_{timestamp}.pdf"
        )

    log(
        f"RECEIVED codes TYPE: {type(codes)}"
    )
    log(
        f"RECEIVED codes CONTENT: {codes!r}"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    settings = resolve_page_settings(
        page_width_mm=page_width_mm,
        page_height_mm=page_height_mm,
        margin_mm=margin_mm,
        code_size_mm=code_size_mm,
        horizontal_shift_mm=(
            horizontal_shift_mm
        ),
        vertical_shift_mm=(
            vertical_shift_mm
        ),
    )

    page_width_mm = settings[
        "page_width_mm"
    ]

    page_height_mm = settings[
        "page_height_mm"
    ]

    margin_mm = settings[
        "margin_mm"
    ]

    code_size_mm = settings[
        "code_size_mm"
    ]

    horizontal_shift_mm = settings[
        "horizontal_shift_mm"
    ]

    vertical_shift_mm = settings[
        "vertical_shift_mm"
    ]

    log(
        f"GENERATOR FILE: "
        f"{__file__}"
    )

    log(
        f"RECEIVED ARGUMENTS: "
        f"page_width_mm="
        f"{page_width_mm!r}, "
        f"page_height_mm="
        f"{page_height_mm!r}, "
        f"margin_mm="
        f"{margin_mm!r}, "
        f"code_size_mm="
        f"{code_size_mm!r}, "
        f"horizontal_shift_mm="
        f"{horizontal_shift_mm!r}, "
        f"vertical_shift_mm="
        f"{vertical_shift_mm!r}"
    )

    page_width = mm_to_points(
        page_width_mm
    )

    page_height = mm_to_points(
        page_height_mm
    )

    margin = mm_to_points(
        margin_mm
    )

    code_size = mm_to_points(
        code_size_mm
    )

    available_width = (
        page_width
        - margin * 2.0
    )

    available_height = (
        page_height
        - margin * 2.0
    )

    actual_size = min(
        code_size,
        available_width,
        available_height,
    )

    actual_size_mm = (
        actual_size
        / 72.0
        * 25.4
    )

    x = mm_to_points(
        margin_mm
        + horizontal_shift_mm
    )

    y = mm_to_points(
        margin_mm
        + vertical_shift_mm
    )

    left_margin = x
    bottom_margin = y

    right_margin = (
        page_width
        - x
        - actual_size
    )

    top_margin = (
        page_height
        - y
        - actual_size
    )

    left_margin_mm = (
        left_margin
        / 72.0
        * 25.4
    )

    bottom_margin_mm = (
        bottom_margin
        / 72.0
        * 25.4
    )

    right_margin_mm = (
        right_margin
        / 72.0
        * 25.4
    )

    top_margin_mm = (
        top_margin
        / 72.0
        * 25.4
    )

    x_mm = (
        x
        / 72.0
        * 25.4
    )

    y_mm = (
        y
        / 72.0
        * 25.4
    )

    log(
        f"PDF layout: "
        f"page={page_width_mm:.2f}x"
        f"{page_height_mm:.2f} mm, "
        f"margin={margin_mm:.2f} mm, "
        f"code={code_size_mm:.2f} mm, "
        f"actual={actual_size_mm:.2f} mm"
    )

    log(
        f"PDF compensation: "
        f"horizontal="
        f"{horizontal_shift_mm:.2f} mm, "
        f"vertical="
        f"{vertical_shift_mm:.2f} mm"
    )

    log(
        f"PDF margins: "
        f"left={left_margin_mm:.2f} mm, "
        f"bottom={bottom_margin_mm:.2f} mm, "
        f"right={right_margin_mm:.2f} mm, "
        f"top={top_margin_mm:.2f} mm"
    )

    log(
        f"DataMatrix position: "
        f"x={x_mm:.2f} mm, "
        f"y={y_mm:.2f} mm, "
        f"size={actual_size_mm:.2f} mm"
    )

    code_list = list(
        codes or []
    )

    total_codes = len(
        code_list
    )

    if total_codes == 0:
        error_message = (
            "Лист 1: код не распознан"
        )

        log(
            "PDF generation stopped: "
            "no codes received"
        )

        return make_result(
            output_path=output_path,
            total_count=0,
            success_count=0,
            errors=[
                error_message,
            ],
            successful_codes=[],
        )

    success_count = 0
    successful_codes = []
    errors = []
    pdf = None

    try:
        pdf = canvas.Canvas(
            str(output_path),
            pagesize=(
                page_width,
                page_height,
            ),
        )

        for index, code_data in enumerate(
            code_list,
            start=1,
        ):
            pdf.setPageSize(
                (
                    page_width,
                    page_height,
                )
            )

            if not is_valid_code(
                code_data
            ):
                error_message = (
                    f"Лист {index}: "
                    "код не распознан"
                )

                errors.append(
                    error_message
                )

                draw_error_page(
                    pdf,
                    "Ошибка распознавания",
                    margin,
                )

                log(
                    f"pdf page {index}: "
                    "no code"
                )

            else:
                try:
                    started_at = (
                        time.perf_counter()
                    )

                    image = (
                        build_datamatrix_image(
                            code_data
                        )
                    )

                    log(
                        f"DataMatrix source image: "
                        f"{image.width}x"
                        f"{image.height} px"
                    )

                    image_bytes = (
                        io.BytesIO()
                    )

                    image.save(
                        image_bytes,
                        format="PNG",
                    )

                    image_bytes.seek(0)

                    pdf.drawImage(
                        ImageReader(
                            image_bytes
                        ),
                        x,
                        y,
                        width=actual_size,
                        height=actual_size,
                        preserveAspectRatio=False,
                        mask="auto",
                    )

                    elapsed = (
                        time.perf_counter()
                        - started_at
                    )

                    log(
                        f"pdf page {index}: "
                        "generated in "
                        f"{format_seconds(elapsed)}"
                    )

                    success_count += 1

                    successful_codes.append(
                        code_data
                    )

                except Exception as error:
                    error_message = (
                        f"Лист {index}: "
                        "ошибка генерации: "
                        f"{error}"
                    )

                    errors.append(
                        error_message
                    )

                    draw_error_page(
                        pdf,
                        "Ошибка генерации",
                        margin,
                    )

                    log(
                        f"pdf page {index}: "
                        f"generation error: "
                        f"{error}"
                    )

            pdf.showPage()

            if progress_callback:
                progress_callback(
                    index,
                    total_codes,
                )

        pdf.save()
        pdf = None

    except Exception as error:
        log(
            f"PDF fatal generation error: "
            f"{error}"
        )

        if pdf is not None:
            try:
                pdf.save()

            except Exception as save_error:
                log(
                    f"PDF emergency save error: "
                    f"{save_error}"
                )

        return make_result(
            output_path=output_path,
            total_count=total_codes,
            success_count=success_count,
            errors=errors,
            fatal_error=str(error),
            successful_codes=(
                successful_codes
            ),
        )

    if not output_path.exists():
        error_message = (
            "PDF-файл не был создан"
        )

        log(
            error_message
        )

        return make_result(
            output_path=output_path,
            total_count=total_codes,
            success_count=success_count,
            errors=errors,
            fatal_error=error_message,
            successful_codes=(
                successful_codes
            ),
        )

    if output_path.stat().st_size == 0:
        error_message = (
            "Создан пустой PDF-файл"
        )

        log(
            error_message
        )

        return make_result(
            output_path=output_path,
            total_count=total_codes,
            success_count=success_count,
            errors=errors,
            fatal_error=error_message,
            successful_codes=(
                successful_codes
            ),
        )

    result = make_result(
        output_path=output_path,
        total_count=total_codes,
        success_count=success_count,
        errors=errors,
        successful_codes=(
            successful_codes
        ),
    )

    if result["is_complete"]:
        log(
            f"PDF saved successfully: "
            f"{output_path}; "
            f"codes={success_count}/"
            f"{total_codes}"
        )

    else:
        log(
            f"PDF saved with errors: "
            f"{output_path}; "
            f"codes={success_count}/"
            f"{total_codes}; "
            f"errors={len(errors)}"
        )

    return result