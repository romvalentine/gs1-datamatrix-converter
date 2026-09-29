import json
import tkinter as tk

from pathlib import Path
from tkinter import ttk


class SettingsPanel(ttk.Frame):
    DEFAULT_LABEL = "По умолчанию"

    def __init__(
        self,
        master,
        settings_file,
    ):
        super().__init__(master)

        self.settings_file = Path(
            settings_file
        )

        self.expanded = False
        self.printers = []

        self.open_var = tk.BooleanVar(
            value=False
        )

        self.print_var = tk.BooleanVar(
            value=False
        )

        self.printer_var = tk.StringVar(
            value=self.DEFAULT_LABEL
        )

        self.width_var = tk.StringVar(
            value="25.4"
        )

        self.height_var = tk.StringVar(
            value="20.4"
        )

        self.gap_var = tk.StringVar(
            value="1.0"
        )

        self.code_size_var = tk.StringVar(
            value="17.0"
        )

        self.orientation_var = tk.StringVar(
            value="Книжная"
        )

        self.scale_var = tk.StringVar(
            value="Без масштабирования"
        )

        self.copies_var = tk.StringVar(
            value="1"
        )

        self.toggle_button = tk.Button(
            self,
            text="▶ Дополнительные действия",
            anchor=tk.W,
            command=self.toggle,
            relief=tk.FLAT,
            cursor="hand2",
        )

        self.toggle_button.pack(
            fill=tk.X
        )

        self.content = ttk.LabelFrame(
            self,
            text="После обработки",
            padding=6,
        )

        self.open_checkbutton = tk.Checkbutton(
            self.content,
            text=(
                "Открыть полученный PDF "
                "после обработки"
            ),
            variable=self.open_var,
            command=self.open_selected,
            anchor=tk.W,
        )

        self.open_checkbutton.pack(
            fill=tk.X
        )

        self.print_checkbutton = tk.Checkbutton(
            self.content,
            text=(
                "Отправить полученный PDF "
                "на печать"
            ),
            variable=self.print_var,
            command=self.print_selected,
            anchor=tk.W,
        )

        self.print_checkbutton.pack(
            fill=tk.X
        )

        printer_frame = tk.Frame(
            self.content
        )

        printer_frame.pack(
            fill=tk.X,
            pady=(8, 0),
        )

        tk.Label(
            printer_frame,
            text="Принтер:",
            anchor=tk.W,
        ).pack(
            side=tk.LEFT,
            padx=(0, 6),
        )

        self.printer_combo = ttk.Combobox(
            printer_frame,
            textvariable=self.printer_var,
            state="readonly",
            width=42,
        )

        self.printer_combo.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
        )

        self.printer_combo.bind(
            "<<ComboboxSelected>>",
            self.on_printer_selected,
        )

        self.refresh_button = tk.Button(
            printer_frame,
            text="Обновить",
            command=self.refresh_printers,
            width=12,
        )

        self.refresh_button.pack(
            side=tk.LEFT,
            padx=(6, 0),
        )

        self.printer_status_label = tk.Label(
            self.content,
            text="",
            fg="gray",
            anchor=tk.W,
        )

        self.printer_status_label.pack(
            fill=tk.X,
            pady=(4, 0),
        )

        size_frame = ttk.LabelFrame(
            self.content,
            text="Параметры страницы",
            padding=6,
        )

        size_frame.pack(
            fill=tk.X,
            pady=(8, 0),
        )

        self.add_entry(
            size_frame,
            "Ширина, мм:",
            self.width_var,
            0,
        )

        self.add_entry(
            size_frame,
            "Высота, мм:",
            self.height_var,
            1,
        )

        self.add_entry(
            size_frame,
            "Зазор, мм:",
            self.gap_var,
            2,
        )

        self.add_entry(
            size_frame,
            "Размер DataMatrix, мм:",
            self.code_size_var,
            3,
        )

        ttk.Label(
            size_frame,
            text="Ориентация:",
        ).grid(
            row=4,
            column=0,
            sticky=tk.W,
            padx=4,
            pady=3,
        )

        self.orientation_combo = ttk.Combobox(
            size_frame,
            textvariable=self.orientation_var,
            values=[
                "Книжная",
                "Альбомная",
            ],
            state="readonly",
            width=19,
        )

        self.orientation_combo.grid(
            row=4,
            column=1,
            sticky=tk.W,
            padx=4,
            pady=3,
        )

        self.orientation_combo.bind(
            "<<ComboboxSelected>>",
            self.on_print_setting_changed,
        )

        ttk.Label(
            size_frame,
            text="Масштаб:",
        ).grid(
            row=5,
            column=0,
            sticky=tk.W,
            padx=4,
            pady=3,
        )

        self.scale_combo = ttk.Combobox(
            size_frame,
            textvariable=self.scale_var,
            values=[
                "Без масштабирования",
                "Вписать",
            ],
            state="readonly",
            width=19,
        )

        self.scale_combo.grid(
            row=5,
            column=1,
            sticky=tk.W,
            padx=4,
            pady=3,
        )

        self.scale_combo.bind(
            "<<ComboboxSelected>>",
            self.on_print_setting_changed,
        )

        self.add_entry(
            size_frame,
            "Количество копий:",
            self.copies_var,
            6,
        )

        self.settings_status_label = tk.Label(
            size_frame,
            text=(
                "Зазор задаётся также "
                "в драйвере Godex."
            ),
            fg="gray",
            anchor=tk.W,
        )

        self.settings_status_label.grid(
            row=7,
            column=0,
            columnspan=2,
            sticky=tk.W,
            padx=4,
            pady=(5, 0),
        )

        self.refresh_printers(
            save=False
        )

        self.load_settings()

    def add_entry(
        self,
        parent,
        text,
        variable,
        row,
    ):
        ttk.Label(
            parent,
            text=text,
        ).grid(
            row=row,
            column=0,
            sticky=tk.W,
            padx=4,
            pady=3,
        )

        entry = ttk.Entry(
            parent,
            textvariable=variable,
            width=22,
        )

        entry.grid(
            row=row,
            column=1,
            sticky=tk.W,
            padx=4,
            pady=3,
        )

        entry.bind(
            "<FocusOut>",
            self.on_print_setting_changed,
        )

    def toggle(self):
        if self.expanded:
            self.content.pack_forget()

            self.toggle_button.config(
                text="▶ Дополнительные действия"
            )

            self.expanded = False

        else:
            self.content.pack(
                fill=tk.X,
                pady=(3, 0),
            )

            self.toggle_button.config(
                text="▼ Дополнительные действия"
            )

            self.expanded = True

    def open_selected(self):
        if self.open_var.get():
            self.print_var.set(False)

        self.save_settings()

    def print_selected(self):
        if self.print_var.get():
            self.open_var.set(False)

        self.save_settings()

    def get_action(self):
        if self.open_var.get():
            return "open"

        if self.print_var.get():
            return "print"

        return "none"

    def get_printer(self):
        printer = self.printer_var.get()

        if (
            not printer
            or printer == self.DEFAULT_LABEL
        ):
            return None

        return printer

    def get_float(
        self,
        variable,
        default,
        minimum,
    ):
        try:
            value = float(
                variable.get().replace(
                    ",",
                    ".",
                )
            )

            if value < minimum:
                return default

            return value

        except (
            TypeError,
            ValueError,
        ):
            return default

    def get_int(
        self,
        variable,
        default,
        minimum,
    ):
        try:
            value = int(
                variable.get()
            )

            if value < minimum:
                return default

            return value

        except (
            TypeError,
            ValueError,
        ):
            return default

    def get_print_settings(self):
        width = self.get_float(
            self.width_var,
            25.4,
            1.0,
        )

        height = self.get_float(
            self.height_var,
            20.4,
            1.0,
        )

        gap = self.get_float(
            self.gap_var,
            1.0,
            0.0,
        )

        code_size = self.get_float(
            self.code_size_var,
            17.0,
            1.0,
        )

        copies = self.get_int(
            self.copies_var,
            1,
            1,
        )

        orientation = (
            "landscape"
            if self.orientation_var.get()
            == "Альбомная"
            else "portrait"
        )

        scale = (
            "fit"
            if self.scale_var.get()
            == "Вписать"
            else "noscale"
        )

        return {
            "label_width_mm": width,
            "label_height_mm": height,
            "label_gap_mm": gap,
            "code_size_mm": code_size,
            "orientation": orientation,
            "scale": scale,
            "copies": copies,
        }

    def on_print_setting_changed(
        self,
        event=None,
    ):
        self.save_settings()

    def set_enabled(
        self,
        enabled=True,
    ):
        if enabled:
            button_state = tk.NORMAL
            combo_state = "readonly"
            entry_state = "normal"

        else:
            button_state = tk.DISABLED
            combo_state = tk.DISABLED
            entry_state = "disabled"

        self.toggle_button.config(
            state=button_state
        )

        self.open_checkbutton.config(
            state=button_state
        )

        self.print_checkbutton.config(
            state=button_state
        )

        self.printer_combo.config(
            state=combo_state
        )

        self.refresh_button.config(
            state=button_state
        )

        for child in (
            self.content.winfo_children()
        ):
            if isinstance(
                child,
                ttk.LabelFrame,
            ):
                for item in (
                    child.winfo_children()
                ):
                    if isinstance(
                        item,
                        ttk.Entry,
                    ):
                        item.config(
                            state=entry_state
                        )

                    elif isinstance(
                        item,
                        ttk.Combobox,
                    ):
                        item.config(
                            state=(
                                combo_state
                            )
                        )

    def get_available_printers(self):
        try:
            import win32print

        except ImportError:
            self.printer_status_label.config(
                text=(
                    "pywin32 не установлен."
                ),
                fg="darkorange",
            )

            return []

        try:
            flags = (
                win32print.PRINTER_ENUM_LOCAL
                | win32print.PRINTER_ENUM_CONNECTIONS
            )

            entries = win32print.EnumPrinters(
                flags,
                None,
                2,
            )

            result = []
            seen = set()

            for entry in entries or []:
                name = None

                if isinstance(entry, dict):
                    name = entry.get(
                        "pPrinterName"
                    )

                elif isinstance(
                    entry,
                    (tuple, list),
                ):
                    if len(entry) >= 3:
                        name = entry[2]

                if not name:
                    continue

                name = str(name)

                if name in seen:
                    continue

                seen.add(name)
                result.append(name)

            result.sort(
                key=str.casefold
            )

            return result

        except Exception as error:
            self.printer_status_label.config(
                text=f"Ошибка: {error}",
                fg="darkorange",
            )

            return []

    def refresh_printers(
        self,
        save=True,
    ):
        self.printers = (
            self.get_available_printers()
        )

        values = [
            self.DEFAULT_LABEL,
            *self.printers,
        ]

        self.printer_combo.config(
            values=values
        )

        if self.printer_var.get() not in values:
            self.printer_var.set(
                self.DEFAULT_LABEL
            )

        self.printer_status_label.config(
            text=(
                f"Доступно принтеров: "
                f"{len(self.printers)}"
                if self.printers
                else "Принтеры не найдены."
            ),
            fg=(
                "gray"
                if self.printers
                else "darkorange"
            ),
        )

        if save:
            self.save_settings()

    def on_printer_selected(
        self,
        event=None,
    ):
        self.save_settings()

    def load_settings(self):
        try:
            if not self.settings_file.exists():
                return

            with self.settings_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            action = data.get(
                "after_action",
                "none",
            )

            self.open_var.set(
                action == "open"
            )

            self.print_var.set(
                action == "print"
            )

            saved_printer = data.get(
                "printer"
            )

            values = list(
                self.printer_combo.cget(
                    "values"
                )
            )

            if saved_printer in values:
                self.printer_var.set(
                    saved_printer
                )

            for variable, key in (
                (
                    self.width_var,
                    "label_width_mm",
                ),
                (
                    self.height_var,
                    "label_height_mm",
                ),
                (
                    self.gap_var,
                    "label_gap_mm",
                ),
                (
                    self.code_size_var,
                    "code_size_mm",
                ),
            ):
                if key in data:
                    variable.set(
                        str(data[key])
                    )

            if data.get(
                "orientation"
            ) == "landscape":
                self.orientation_var.set(
                    "Альбомная"
                )

            if data.get(
                "scale"
            ) == "fit":
                self.scale_var.set(
                    "Вписать"
                )

            if "copies" in data:
                self.copies_var.set(
                    str(data["copies"])
                )

        except Exception:
            pass

    def save_settings(self):
        try:
            self.settings_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            data = {
                "after_action": (
                    self.get_action()
                ),
                "printer": self.get_printer(),
                **self.get_print_settings(),
            }

            with self.settings_file.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

        except Exception:
            pass