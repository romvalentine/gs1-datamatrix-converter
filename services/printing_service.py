import os
import subprocess
import sys

from logger import log


SUMATRA_PATH = (
    r"C:\Users\u143d\AppData\Local"
    r"\SumatraPDF\SumatraPDF.exe"
)


def open_pdf(
    path,
):
    path = str(path)

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"PDF не найден: {path}"
        )

    if sys.platform == "win32":
        os.startfile(path)

    elif sys.platform == "darwin":
        subprocess.Popen(
            [
                "open",
                path,
            ]
        )

    else:
        subprocess.Popen(
            [
                "xdg-open",
                path,
            ]
        )


def print_pdf(
    path,
    printer_name=None,
    print_settings=None,
):
    path = os.path.abspath(
        str(path)
    )

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"PDF не найден: {path}"
        )

    if print_settings is None:
        print_settings = {
            "orientation": "portrait",
            "scale": "noscale",
            "copies": 1,
        }

    orientation = print_settings.get(
        "orientation",
        "portrait",
    )

    scale = print_settings.get(
        "scale",
        "noscale",
    )

    copies = print_settings.get(
        "copies",
        1,
    )

    try:
        copies = int(copies)

    except (
        TypeError,
        ValueError,
    ):
        copies = 1

    copies = max(
        1,
        copies,
    )

    settings_parts = [
        scale,
        orientation,
    ]

    if copies > 1:
        settings_parts.append(
            f"{copies}x"
        )

    settings_text = ",".join(
        settings_parts
    )

    if sys.platform != "win32":
        command = [
            "lp",
            "-n",
            str(copies),
            path,
        ]

        if printer_name:
            command = [
                "lp",
                "-d",
                printer_name,
                "-n",
                str(copies),
                path,
            ]

        subprocess.run(
            command,
            check=True,
        )

        return

    if not os.path.exists(
        SUMATRA_PATH
    ):
        raise RuntimeError(
            "SumatraPDF не найден:\n"
            f"{SUMATRA_PATH}"
        )

    if (
        not printer_name
        or printer_name == "По умолчанию"
    ):
        command = [
            SUMATRA_PATH,
            "-silent",
            "-print-to-default",
            "-print-settings",
            settings_text,
            path,
        ]

    else:
        command = [
            SUMATRA_PATH,
            "-silent",
            "-print-to",
            printer_name,
            "-print-settings",
            settings_text,
            path,
        ]

    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60,
    )

    if process.returncode != 0:
        details = (
            process.stderr
            or process.stdout
            or "нет дополнительной информации"
        )

        raise RuntimeError(
            "SumatraPDF не смог "
            "напечатать PDF.\n\n"
            f"{details}"
        )

    log(
        "PDF отправлен на принтер: "
        f"{printer_name or 'по умолчанию'}"
    )