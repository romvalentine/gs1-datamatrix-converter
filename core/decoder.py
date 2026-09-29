import os
import sys
import time
import re


if sys.platform == "win32":
    try:
        current_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        project_dir = os.path.dirname(
            current_dir
        )

        if hasattr(
            os,
            "add_dll_directory",
        ):
            os.add_dll_directory(
                project_dir
            )

    except Exception:
        pass


try:
    from pylibdmtx.pylibdmtx import (
        decode,
    )

except ImportError as error:
    raise ImportError(
        "Библиотека pylibdmtx не установлена.\n"
        "Выполните:\n"
        "python -m pip install pylibdmtx"
    ) from error

except OSError as error:
    raise OSError(
        f"Ошибка загрузки libdmtx: {error}"
    ) from error


from config import (
    DECODE_SHRINK,
    DECODE_TIMEOUT,
    FALLBACK_ONLY_IF_EMPTY,
    USE_OPENCV_FALLBACK,
)

from logger import log


def is_valid_datamatrix_code(code: str) -> bool:
    """
    Проверяет, похож ли код на настоящий DataMatrix.
    Отфильтровывает ложные срабатывания от кодов на чёрном фоне.
    """
    if not code or not isinstance(code, str):
        return False
    
    # Убираем пробелы по краям
    code = code.strip()
    
    # Слишком короткие коды — скорее всего мусор
    if len(code) < 10:
        return False
    
    # Для GS1 DataMatrix — проверяем формат
    # Код должен начинаться с 01 (GTIN)
    if code.startswith("01"):
        return True
    
    # Проверяем на явный мусор (слишком много спецсимволов)
    # Исключаем \x1d (GS), пробелы, скобки, дефис
    special_chars = sum(
        1 for c in code 
        if not c.isalnum() 
        and c not in ' ()-\x1d'  # ← Добавили \x1d
    )
    if special_chars > len(code) * 0.4:  # Увеличили с 30% до 40%
        return False
    
    # Проверяем наличие идентификаторов приложений GS1
    if '(' in code and ')' in code:
        valid_ais = [
            '01', '21', '17', '10', '11', 
            '15', '30', '37', '240', '414', '416',
        ]
        
        for ai in valid_ais:
            if f'({ai})' in code:
                return True
        
        ai_pattern = r'\(\d{2,4}\)'
        if re.search(ai_pattern, code):
            return True
        
        return False
    
    # Для обычных DataMatrix — проверяем состав
    alnum_chars = sum(1 for c in code if c.isalnum())
    if alnum_chars >= len(code) * 0.5:
        return True
    
    return False


def normalize_specific_output(
    raw: str,
) -> str:
    if raw is None:
        return ""

    value = str(raw).strip()

    if value.startswith("]d2"):
        value = value[3:]

    if not value.startswith("01"):
        return value

    if len(value) < 16:
        return value

    gtin = value[2:16]
    rest = value[16:]

    if rest.startswith("\x1d"):
        rest = rest[1:]

    if not rest.startswith("21"):
        return "01" + gtin + rest

    rest = rest[2:]

    separator_index = rest.find(
        "\x1d"
    )

    if separator_index == -1:
        serial = rest
        tail = ""

    else:
        serial = rest[:separator_index]
        tail = rest[separator_index:]

    return (
        "01"
        + gtin
        + "21"
        + serial
        + tail
    )


def raw_item_to_string(
    item,
) -> str:
    if item is None:
        return ""

    if isinstance(item, str):
        return item

    if isinstance(item, bytes):
        return item.decode(
            "utf-8",
            errors="replace",
        )

    data = getattr(
        item,
        "data",
        None,
    )

    if data is None:
        return str(item)

    if isinstance(data, bytes):
        return data.decode(
            "utf-8",
            errors="replace",
        )

    return str(data)


def _opencv_values(
    result,
):
    if not isinstance(result, tuple):
        return []

    if len(result) < 2:
        return []

    values = result[1]

    if isinstance(values, str):
        return [values]

    return values or []


def opencv_decode(
    image,
    label="",
):
    try:
        import cv2
        import numpy as np

    except ImportError:
        log(
            "OpenCV fallback skipped: "
            "opencv-contrib-python "
            "не установлен"
        )

        return []

    try:
        if hasattr(
            cv2,
            "barcode_BarcodeDetector",
        ):
            detector = (
                cv2.barcode_BarcodeDetector()
            )

        elif (
            hasattr(cv2, "barcode")
            and hasattr(
                cv2.barcode,
                "BarcodeDetector",
            )
        ):
            detector = (
                cv2.barcode.BarcodeDetector()
            )

        else:
            log(
                "OpenCV BarcodeDetector "
                "недоступен"
            )

            return []

        log(
            f"OpenCV detector: "
            f"{type(detector).__name__}, "
            f"label={label}, "
            f"image={image.width}x"
            f"{image.height}"
        )

        rgb_image = image.convert(
            "RGB"
        )

        array = np.asarray(
            rgb_image
        )

        opencv_image = cv2.cvtColor(
            array,
            cv2.COLOR_RGB2BGR,
        )

        values = []

        try:
            result = (
                detector.detectAndDecodeWithType(
                    opencv_image
                )
            )

            decoded_values = _opencv_values(
                result
            )

        except Exception:
            try:
                result = (
                    detector.detectAndDecode(
                        opencv_image
                    )
                )

                decoded_values = _opencv_values(
                    result
                )

            except Exception as error:
                log(
                    f"OpenCV decode({label}) "
                    f"error: {error}"
                )

                return []

        for value in decoded_values:
            if not value:
                continue

            value = normalize_specific_output(
                raw_item_to_string(value)
            )

            # Добавляем валидацию кода
            if value and is_valid_datamatrix_code(value):
                if value not in values:
                    values.append(value)
            elif value:
                log(
                    f"OpenCV decode({label}) "
                    f"invalid code skipped: {value}"
                )

        if values:
            log(
                f"OpenCV decode({label}) "
                f"-> {len(values)} кодов"
            )

        else:
            log(
                f"OpenCV decode({label}) "
                "-> 0 кодов"
            )

        return values

    except Exception as error:
        log(
            f"OpenCV fallback({label}) "
            f"error: {error}"
        )

        return []


def decode_image(
    image,
    label="",
    stop_event=None,
):
    if (
        stop_event is not None
        and stop_event.is_set()
    ):
        return []

    started_at = time.perf_counter()

    try:
        try:
            decoded = decode(
                image,
                timeout=DECODE_TIMEOUT,
                shrink=DECODE_SHRINK,
            )

        except TypeError:
            decoded = decode(
                image,
                timeout=DECODE_TIMEOUT,
            )

        elapsed = (
            time.perf_counter()
            - started_at
        )

        # Фильтруем невалидные коды
        valid_decoded = []
        for item in decoded or []:
            try:
                code_str = raw_item_to_string(item)
                if is_valid_datamatrix_code(code_str):
                    valid_decoded.append(item)
                else:
                    log(
                        f"decode({label}) "
                        f"invalid code skipped: {code_str}"
                    )
            except Exception as error:
                log(
                    f"decode({label}) validation error: {error}"
                )
                # Если ошибка валидации — всё равно добавляем
                valid_decoded.append(item)

        count = len(valid_decoded)

        log(
            f"decode({label}) -> "
            f"{count} кодов за "
            f"{elapsed:.2f} сек"
        )

        if valid_decoded:
            return valid_decoded

        if (
            USE_OPENCV_FALLBACK
            and FALLBACK_ONLY_IF_EMPTY
            and not (
                stop_event is not None
                and stop_event.is_set()
            )
        ):
            log(
                f"OpenCV fallback start: "
                f"{label}"
            )

            return opencv_decode(
                image,
                label,
            )

        return []

    except Exception as error:
        elapsed = (
            time.perf_counter()
            - started_at
        )

        log(
            f"decode({label}) -> "
            f"ошибка за "
            f"{elapsed:.2f} сек: "
            f"{error}"
        )

        if (
            USE_OPENCV_FALLBACK
            and not (
                stop_event is not None
                and stop_event.is_set()
            )
        ):
            log(
                f"OpenCV fallback start: "
                f"{label}"
            )

            return opencv_decode(
                image,
                label,
            )

        return []


def decoded_to_strings(
    decoded,
):
    result = []

    for item in decoded or []:
        try:
            raw = raw_item_to_string(
                item
            )

            value = normalize_specific_output(
                raw
            )

            if value:
                result.append(value)

        except Exception as error:
            log(
                f"decode result error: "
                f"{error}"
            )

    return result


def collect_codes(
    decoded,
    found,
    codes,
):
    for code in decoded_to_strings(
        decoded
    ):
        # Дополнительная проверка валидности
        if not is_valid_datamatrix_code(code):
            log(
                f"collect_codes: invalid code skipped: {code}"
            )
            continue
        
        if code not in found:
            found.add(code)
            codes.append(code)


def code_to_display(
    code,
):
    if code is None:
        return ""

    return str(code).replace(
        "\x1d",
        "<GS>",
    )


def code_to_raw(
    code,
):
    if code is None:
        return ""

    return str(code)


def has_gs1_separator(
    code,
):
    if code is None:
        return False

    return "\x1d" in str(code)


def is_probable_gs1(
    code,
):
    if code is None:
        return False

    value = str(code)

    return (
        value.startswith("01")
        and len(value) >= 16
    )