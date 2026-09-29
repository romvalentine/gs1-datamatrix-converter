import tkinter as tk

from tkinter import ttk


MODE_LABELS = {
    "Быстрый режим": "fast",
    "Точный режим": "safe",
    "Режим фото": "photo",
    "Multi-режим": "multi",
}


def show_incomplete_dialog(
    parent,
    result,
    current_mode,
):
    dialog = tk.Toplevel(
        parent
    )

    dialog.title(
        "Проверка кодов"
    )

    dialog.resizable(
        False,
        False,
    )

    dialog.transient(
        parent
    )

    dialog.grab_set()

    selected_action = {
        "value": "cancel",
    }

    total_count = result.get(
        "total_count",
        0,
    )

    success_count = result.get(
        "success_count",
        0,
    )

    failed_count = result.get(
        "failed_count",
        0,
    )

    errors = result.get(
        "errors",
        [],
    )

    error_lines = []

    for error in errors:
        error_text = str(
            error
        )

        error_text = (
            error_text.replace(
                "Страница",
                "Лист",
                1,
            )
        )

        error_lines.append(
            error_text
        )

    if not error_lines:
        error_lines.append(
            "Лист не определён"
        )

    error_text = "\n".join(
        error_lines
    )

    # Извлекаем номера листов с ошибками
    error_pages = []
    for error in errors:
        try:
            if error.startswith('Лист '):
                page_num = int(error.split(':')[0].replace('Лист ', '').strip())
                error_pages.append(page_num)
        except:
            pass

    tk.Label(
        dialog,
        text=(
            "Не все коды были успешно "
            "распознаны или созданы."
        ),
        font=(
            "Arial",
            10,
            "bold",
        ),
        justify="left",
        anchor="w",
    ).pack(
        fill="x",
        padx=20,
        pady=(
            15,
            8,
        ),
    )

    tk.Label(
        dialog,
        text=error_text,
        fg="#b00020",
        justify="left",
        anchor="w",
    ).pack(
        fill="x",
        padx=20,
        pady=(
            0,
            8,
        ),
    )

    tk.Label(
        dialog,
        text=(
            f"Распознано: "
            f"{success_count} из "
            f"{total_count}\n"
            f"Ошибок: {failed_count}\n"
            f"Текущий режим: "
            f"{current_mode}"
        ),
        justify="left",
        anchor="w",
    ).pack(
        fill="x",
        padx=20,
        pady=(
            0,
            12,
        ),
    )

    tk.Label(
        dialog,
        text=(
            "Распечатать то, что "
            "распозналось без ошибок?"
        ),
        justify="left",
        anchor="w",
    ).pack(
        fill="x",
        padx=20,
        pady=(
            0,
            5,
        ),
    )

    actions_frame = tk.Frame(
        dialog
    )

    actions_frame.pack(
        padx=20,
        pady=(
            0,
            15,
        ),
    )

    def print_recognized():
        selected_action[
            "value"
        ] = "print_recognized"

        dialog.destroy()

    def cancel():
        selected_action[
            "value"
        ] = "cancel"

        dialog.destroy()

    tk.Button(
        actions_frame,
        text=(
            "Распечатать "
            "распознанное"
        ),
        width=25,
        command=print_recognized,
    ).pack(
        side=tk.LEFT,
        padx=(
            0,
            8,
        ),
    )

    tk.Button(
        actions_frame,
        text="Отмена",
        width=14,
        command=cancel,
    ).pack(
        side=tk.LEFT,
    )

    # Кнопка "Обработать только ошибки"
    if error_pages:
        def retry_errors():
            selected_action[
                "value"
            ] = "retry_errors"
            dialog.destroy()

        tk.Button(
            actions_frame,
            text="🔄 Обработать ошибки",
            width=18,
            command=retry_errors,
            bg="#e0f0ff",
        ).pack(
            side=tk.LEFT,
            padx=8,
        )

    tk.Label(
        dialog,
        text="Выбрать другой режим:",
        justify="left",
        anchor="w",
    ).pack(
        fill="x",
        padx=20,
        pady=(
            0,
            5,
        ),
    )

    mode_frame = tk.Frame(
        dialog
    )

    mode_frame.pack(
        padx=20,
        pady=(
            0,
            15,
        ),
    )

    mode_names = list(
        MODE_LABELS.keys()
    )

    mode_var = tk.StringVar(
        value=(
            mode_names[0]
        )
    )

    mode_box = ttk.Combobox(
        mode_frame,
        textvariable=mode_var,
        values=mode_names,
        state="readonly",
        width=24,
    )

    mode_box.pack(
        side=tk.LEFT,
    )

    def choose_mode():
        mode_name = mode_var.get()

        new_mode = MODE_LABELS.get(
            mode_name
        )

        if new_mode:
            selected_action[
                "value"
            ] = (
                f"mode:{new_mode}"
            )

        dialog.destroy()

    tk.Button(
        mode_frame,
        text="Проверить",
        width=14,
        command=choose_mode,
    ).pack(
        side=tk.LEFT,
        padx=8,
    )

    dialog.protocol(
        "WM_DELETE_WINDOW",
        cancel,
    )

    dialog.update_idletasks()

    parent.wait_window(
        dialog
    )

    return selected_action[
        "value"
    ]