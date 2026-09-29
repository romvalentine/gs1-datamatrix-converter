import io
import time

from pathlib import Path

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from logger import format_seconds, log


def mm_to_points(
    value_mm,
):
    return value_mm * 72 / 25.4


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

    if text.startswith("{FNC1}"):
        text = text[len("{FNC1}"):]

    payload = DataMatrixData(
        FNC1,
        text,
        encoding="ascii",
    )

    encoder = DataMatrixEncoder(
        payload
    )

    return encoder.get_pilimage()


def generate_pdf_with_codes(
    codes,
    output_path,
    page_width_mm=25.4,
    page_height_mm=20.4,
    margin_mm=0.0,
    code_size_mm=17.0,
    progress_callback=None,
):
    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
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

    log(
        f"generate PDF: "
        f"{output_path}"
    )

    pdf = canvas.Canvas(
        str(output_path),
        pagesize=(
            page_width,
            page_height,
        ),
    )

    success_count = 0
    total_codes = len(
        codes or []
    )

    for index, code_data in enumerate(
        codes or [],
        start=1,
    ):
        pdf.setPageSize(
            (
                page_width,
                page_height,
            )
        )

        if code_data is None:
            pdf.setFont(
                "Helvetica",
                7,
            )

            pdf.drawString(
                margin,
                margin,
                "Ошибка распознавания",
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

                image_bytes = (
                    io.BytesIO()
                )

                image.save(
                    image_bytes,
                    format="PNG",
                )

                image_bytes.seek(0)

                available_width = (
                    page_width
                    - margin * 2
                )

                available_height = (
                    page_height
                    - margin * 2
                )

                actual_size = min(
                    code_size,
                    available_width,
                    available_height,
                )

                x = (
                    page_width
                    - actual_size
                ) / 2

                y = (
                    page_height
                    - actual_size
                ) / 2
                
                y += mm_to_points(1.5)

                pdf.drawImage(
                    ImageReader(
                        image_bytes
                    ),
                    x,
                    y,
                    width=actual_size,
                    height=actual_size,
                    preserveAspectRatio=True,
                    mask="auto",
                )

                elapsed = (
                    time.perf_counter()
                    - started_at
                )

                log(
                    f"pdf page {index}: "
                    f"generated in "
                    f"{format_seconds(elapsed)}"
                )

                success_count += 1

            except Exception as error:
                pdf.setFont(
                    "Helvetica",
                    7,
                )

                pdf.drawString(
                    margin,
                    margin,
                    "Ошибка генерации",
                )

                log(
                    f"pdf page {index}: "
                    f"generation error for "
                    f"{code_data}: "
                    f"{error}"
                )

        pdf.showPage()

        if progress_callback:
            progress_callback(
                index,
                total_codes,
            )

    pdf.save()

    log(
        f"PDF saved: "
        f"{output_path}"
    )

    return (
        str(output_path),
        success_count,
    )