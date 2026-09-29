from pathlib import Path

from config import get_page_settings

from pdf.generator import generate_pdf_with_codes


def create_pdf(
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
    page_settings = get_page_settings()

    if page_width_mm is None:
        page_width_mm = page_settings[
            "page_width_mm"
        ]

    if page_height_mm is None:
        page_height_mm = page_settings[
            "page_height_mm"
        ]

    if margin_mm is None:
        margin_mm = page_settings[
            "margin_mm"
        ]

    if code_size_mm is None:
        code_size_mm = page_settings[
            "code_size_mm"
        ]

    if horizontal_shift_mm is None:
        horizontal_shift_mm = page_settings[
            "horizontal_shift_mm"
        ]

    if vertical_shift_mm is None:
        vertical_shift_mm = page_settings[
            "vertical_shift_mm"
        ]

    return generate_pdf_with_codes(
        codes=codes,
        output_path=output_path,
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
        progress_callback=(
            progress_callback
        ),
    )


def create_pdf_from_codes(
    codes,
    output_path=None,
    progress_callback=None,
):
    if not codes:
        return make_empty_result(
            "Нет кодов для генерации PDF"
        )

    page_settings = get_page_settings()

    if output_path is None:
        project_dir = Path(
            __file__
        ).parent.parent

        output_path = (
            project_dir
            / "manual_codes.pdf"
        )

    else:
        output_path = Path(
            output_path
        )

    return generate_pdf_with_codes(
        codes=codes,
        output_path=output_path,
        page_width_mm=page_settings[
            "page_width_mm"
        ],
        page_height_mm=page_settings[
            "page_height_mm"
        ],
        margin_mm=page_settings[
            "margin_mm"
        ],
        code_size_mm=page_settings[
            "code_size_mm"
        ],
        horizontal_shift_mm=page_settings[
            "horizontal_shift_mm"
        ],
        vertical_shift_mm=page_settings[
            "vertical_shift_mm"
        ],
        progress_callback=progress_callback,
    )


def create_recognized_pdf(
    generation_result,
    output_path,
    page_width_mm=None,
    page_height_mm=None,
    margin_mm=None,
    code_size_mm=None,
    horizontal_shift_mm=None,
    vertical_shift_mm=None,
    progress_callback=None,
):
    if not generation_result:
        return make_empty_result(
            "Нет результата генерации"
        )

    successful_codes = generation_result.get(
        "successful_codes",
        [],
    )

    if not successful_codes:
        return make_empty_result(
            (
                "Нет распознанных кодов "
                "для создания PDF"
            )
        )

    source_path = Path(
        output_path
    )

    recognized_path = (
        source_path.with_name(
            source_path.stem
            + "_распознанные"
            + source_path.suffix
        )
    )

    return create_pdf(
        codes=successful_codes,
        output_path=recognized_path,
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
        progress_callback=(
            progress_callback
        ),
    )


def make_empty_result(
    error_text,
):
    return {
        "output_path": None,
        "total_count": 0,
        "success_count": 0,
        "failed_count": 0,
        "successful_codes": [],
        "errors": [
            str(error_text),
        ],
        "fatal_error": None,
        "is_complete": False,
        "has_errors": True,
    }


def is_complete(
    result,
):
    if not isinstance(
        result,
        dict,
    ):
        return False

    return bool(
        result.get(
            "is_complete",
            False,
        )
    )


def has_errors(
    result,
):
    if not isinstance(
        result,
        dict,
    ):
        return True

    return bool(
        result.get(
            "has_errors",
            True,
        )
    )


def get_output_path(
    result,
):
    if not isinstance(
        result,
        dict,
    ):
        return None

    output_path = result.get(
        "output_path"
    )

    if not output_path:
        return None

    return Path(
        output_path
    )


def get_successful_codes(
    result,
):
    if not isinstance(
        result,
        dict,
    ):
        return []

    return list(
        result.get(
            "successful_codes",
            [],
        )
    )


def get_error_text(
    result,
):
    if not isinstance(
        result,
        dict,
    ):
        return "Нет результата генерации"

    errors = result.get(
        "errors",
        [],
    )

    if errors:
        return "\n".join(
            str(error)
            for error in errors
        )

    fatal_error = result.get(
        "fatal_error"
    )

    if fatal_error:
        return str(
            fatal_error
        )

    return "Неизвестная ошибка"