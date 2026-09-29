import json
import tkinter as tk

from pathlib import Path
from tkinter import messagebox
from tkinter import ttk

from config import update_page_settings

try:
    import win32print
except ImportError:
    win32print = None


DEFAULT_PAGE_SETTINGS = {
    "page_width_mm": 20.0,
    "page_height_mm": 20.0,
    "margin_mm": 1.5,
    "code_size_mm": 17.0,
    "horizontal_shift_mm": -1.0,
    "vertical_shift_mm": 0.0,
}

COLORS = {
    "bg": "#f5f7fa",
    "card_bg": "#ffffff",
    "accent": "#4a9eff",
    "accent_dark": "#3a8eef",
    "success": "#28a745",
    "danger": "#dc3545",
    "text": "#2c3e50",
    "border": "#e1e5eb",
}


class SettingsPanel(tk.LabelFrame):
    def __init__(self, parent, settings_file):
        super().__init__(
            parent,
            text="⚙ Настройки печати",
            padx=10,
            pady=10,
            bg=COLORS["card_bg"],
            fg=COLORS["text"],
        )

        self.settings_file = Path(settings_file)
        self.settings_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.profiles = {}
        self.entries = []
        self.settings_window = None
        self.active_panel = None
        self.action_buttons = {}

        self._init_variables()
        self.build_interface()
        self.load_settings()
        self.refresh_printers()
        self.apply_page_settings()

    def _init_variables(self):
        self.profile_name_var = tk.StringVar()
        self.profile_var = tk.StringVar()

        self.width_var = tk.StringVar(value="20.0")
        self.height_var = tk.StringVar(value="20.0")
        self.margin_var = tk.StringVar(value="1.5")
        self.code_size_var = tk.StringVar(value="17.0")
        self.horizontal_shift_var = tk.StringVar(value="-1.0")
        self.vertical_shift_var = tk.StringVar(value="0.0")

        self.printer_var = tk.StringVar()
        self.copies_var = tk.StringVar(value="1")
        self.dpi_var = tk.StringVar(value="300")

        # Пустое значение означает: действие не выбрано.
        self.action_var = tk.StringVar(value="")

    def open_in_window(self, parent):
        if (
            self.settings_window is not None
            and self.settings_window.winfo_exists()
        ):
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        self.settings_window = tk.Toplevel(parent)
        self.settings_window.title("⚙ Настройки печати")
        self.settings_window.geometry("750x550+200+200")
        self.settings_window.minsize(700, 500)
        self.settings_window.resizable(True, True)

        # Создаётся отдельная панель, поскольку Tkinter
        # не позволяет переносить один и тот же виджет в другой root.
        panel = SettingsPanel(
            self.settings_window,
            settings_file=self.settings_file,
        )

        self.active_panel = panel

        panel.pack(
            fill=tk.BOTH,
            expand=True,
            padx=15,
            pady=15,
        )

        close_btn = tk.Button(
            self.settings_window,
            text="✕ Закрыть",
            command=lambda: self._close_window_with_panel(panel),
            bg=COLORS["danger"],
            fg="white",
            activebackground=COLORS["danger"],
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            font=("Arial", 10, "bold"),
        )
        close_btn.pack(
            side=tk.BOTTOM,
            fill=tk.X,
            padx=15,
            pady=(0, 15),
        )

        self.settings_window.protocol(
            "WM_DELETE_WINDOW",
            lambda: self._close_window_with_panel(panel),
        )

        self.settings_window.focus_force()

    def _close_window_with_panel(self, panel):
        """Сохраняет данные окна и обновляет скрытую основную панель."""
        if panel.winfo_exists():
            panel.save_settings()

        # Основная панель должна получить новые данные,
        # чтобы обработка использовала именно выбранные настройки.
        self.load_settings()
        self.refresh_printers()

        if panel.winfo_exists():
            panel.destroy()

        if (
            self.settings_window is not None
            and self.settings_window.winfo_exists()
        ):
            self.settings_window.destroy()

        self.active_panel = None
        self.settings_window = None

    def close_window(self):
        if self.active_panel is not None:
            self._close_window_with_panel(self.active_panel)

    def build_interface(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        left = tk.Frame(
            self,
            bg=COLORS["card_bg"],
        )
        left.grid(
            row=0,
            column=0,
            sticky="n",
            padx=(0, 15),
        )

        right = tk.Frame(
            self,
            bg=COLORS["card_bg"],
        )
        right.grid(
            row=0,
            column=1,
            sticky="n",
            padx=(15, 0),
        )

        self._build_profile_section(left)
        self._build_page_section(left)

        self._build_printer_section(right)
        self._build_copies_dpi_section(right)
        self._build_action_section(right)
        self._build_preview_section(right)
        self._build_buttons_section(right)

    def _build_profile_section(self, parent):
        tk.Label(
            parent,
            text="Профиль:",
            bg=COLORS["card_bg"],
            fg=COLORS["text"],
            font=("Arial", 10, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 4),
        )

        self.profile_box = ttk.Combobox(
            parent,
            textvariable=self.profile_var,
            state="readonly",
            width=25,
        )
        self.profile_box.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )
        self.profile_box.bind(
            "<<ComboboxSelected>>",
            self.on_profile_selected,
        )

        tk.Label(
            parent,
            text="Новый профиль:",
            bg=COLORS["card_bg"],
            fg=COLORS["text"],
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=(0, 2),
        )

        self.profile_name_entry = tk.Entry(
            parent,
            textvariable=self.profile_name_var,
            width=25,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        self.profile_name_entry.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        profile_buttons = tk.Frame(
            parent,
            bg=COLORS["card_bg"],
        )
        profile_buttons.grid(
            row=4,
            column=0,
            sticky="w",
            pady=(0, 12),
        )

        tk.Button(
            profile_buttons,
            text="Сохранить",
            command=self.save_profile,
            bg=COLORS["accent"],
            fg="white",
            relief=tk.RAISED,
            bd=2,
        ).pack(
            side=tk.LEFT,
            padx=3,
        )

        tk.Button(
            profile_buttons,
            text="Удалить",
            command=self.delete_profile,
            bg=COLORS["danger"],
            fg="white",
            relief=tk.RAISED,
            bd=2,
        ).pack(
            side=tk.LEFT,
            padx=3,
        )

    def _build_page_section(self, parent):
        tk.Label(
            parent,
            text="📄 Страница:",
            bg=COLORS["card_bg"],
            fg=COLORS["text"],
            font=("Arial", 10, "bold"),
        ).grid(
            row=5,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        self.add_entry(parent, "Ширина (мм):", self.width_var, 6, 8)
        self.add_entry(parent, "Высота (мм):", self.height_var, 8, 8)
        self.add_entry(parent, "Поле (мм):", self.margin_var, 10, 8)
        self.add_entry(parent, "Код (мм):", self.code_size_var, 12, 8)
        self.add_entry(
            parent,
            "↔ Горизонт.:",
            self.horizontal_shift_var,
            14,
            8,
        )
        self.add_entry(
            parent,
            "↕ Вертик.:",
            self.vertical_shift_var,
            16,
            8,
        )

    def _build_printer_section(self, parent):
        tk.Label(
            parent,
            text="🖨 Принтер:",
            bg=COLORS["card_bg"],
            fg=COLORS["text"],
            font=("Arial", 10, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 4),
        )

        printer_frame = tk.Frame(
            parent,
            bg=COLORS["card_bg"],
        )
        printer_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )
        printer_frame.columnconfigure(0, weight=1)

        self.printer_box = ttk.Combobox(
            printer_frame,
            textvariable=self.printer_var,
            state="normal",
            width=25,
        )
        self.printer_box.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        tk.Button(
            printer_frame,
            text="↻",
            command=self.refresh_printers,
            width=3,
            bg=COLORS["bg"],
            relief=tk.RAISED,
            bd=1,
        ).grid(
            row=0,
            column=1,
            padx=(5, 0),
        )

    def _build_copies_dpi_section(self, parent):
        frame = tk.Frame(
            parent,
            bg=COLORS["card_bg"],
        )
        frame.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        tk.Label(
            frame,
            text="Копии:",
            bg=COLORS["card_bg"],
            fg=COLORS["text"],
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        tk.Label(
            frame,
            text="DPI:",
            bg=COLORS["card_bg"],
            fg=COLORS["text"],
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(20, 0),
        )

        self.copies_entry = tk.Entry(
            frame,
            textvariable=self.copies_var,
            width=7,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        self.copies_entry.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(2, 0),
        )

        self.dpi_entry = tk.Entry(
            frame,
            textvariable=self.dpi_var,
            width=7,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        self.dpi_entry.grid(
            row=1,
            column=1,
            sticky="w",
            padx=(20, 0),
            pady=(2, 0),
        )

    def _build_action_section(self, parent):
        tk.Label(
            parent,
            text="⚡ После обработки:",
            bg=COLORS["card_bg"],
            fg=COLORS["text"],
            font=("Arial", 10, "bold"),
        ).grid(
            row=3,
            column=0,
            sticky="w",
            pady=(12, 4),
        )

        action_frame = tk.Frame(
            parent,
            bg=COLORS["card_bg"],
        )
        action_frame.grid(
            row=4,
            column=0,
            sticky="w",
        )

        actions = [
            ("Ничего", "none"),
            ("Открыть", "open"),
            ("Печать", "print"),
            ("Excel", "excel"),
        ]

        for index, (text, value) in enumerate(actions):
            button = tk.Button(
                action_frame,
                text=text,
                command=lambda value=value: self.set_action(value),
                bg="#f0f0f0",
                fg=COLORS["text"],
                activebackground=COLORS["accent"],
                activeforeground="white",
                relief=tk.RAISED,
                bd=2,
                width=10,
                font=("Arial", 9),
            )
            button.grid(
                row=0,
                column=index,
                padx=4,
            )
            self.action_buttons[value] = button

        self.update_action_buttons()

    def set_action(self, action):
        """Устанавливает обычное действие после обработки."""
        self.action_var.set(action)
        self.update_action_buttons()

        if hasattr(self, "preview_btn"):
            self.preview_btn.config(
                bg="#f0f0f0",
                fg=COLORS["text"],
                relief=tk.RAISED,
            )

        self.save_settings()

    def update_action_buttons(self):
        current = self.action_var.get()

        for value, button in self.action_buttons.items():
            if value == current:
                button.config(
                    bg=COLORS["accent"],
                    fg="white",
                    relief=tk.SUNKEN,
                )
            else:
                button.config(
                    bg="#f0f0f0",
                    fg=COLORS["text"],
                    relief=tk.RAISED,
                )

    def _build_preview_section(self, parent):
        self.preview_btn = tk.Button(
            parent,
            text="👁 Предпросмотр",
            command=self.toggle_preview,
            bg="#f0f0f0",
            fg=COLORS["text"],
            activebackground=COLORS["accent"],
            activeforeground="white",
            font=("Arial", 11, "bold"),
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            width=18,
        )
        self.preview_btn.grid(
            row=5,
            column=0,
            sticky="w",
            pady=8,
        )

    def toggle_preview(self):
        """Включает/выключает отдельный режим предпросмотра."""
        if self.action_var.get() == "preview":
            self.action_var.set("")
            self.preview_btn.config(
                bg="#f0f0f0",
                fg=COLORS["text"],
                relief=tk.RAISED,
            )
        else:
            self.action_var.set("preview")
            self.update_action_buttons()
            self.preview_btn.config(
                bg=COLORS["accent"],
                fg="white",
                relief=tk.SUNKEN,
            )

        self.save_settings()

    def _build_buttons_section(self, parent):
        frame = tk.Frame(
            parent,
            bg=COLORS["card_bg"],
        )
        frame.grid(
            row=6,
            column=0,
            sticky="w",
            pady=8,
        )

        tk.Button(
            frame,
            text="Сохранить",
            command=self.save_settings,
            bg=COLORS["success"],
            fg="white",
            relief=tk.RAISED,
            bd=2,
        ).pack(
            side=tk.LEFT,
            padx=3,
        )

        tk.Button(
            frame,
            text="Сброс страницы",
            command=self.reset_page_settings,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            relief=tk.RAISED,
            bd=2,
        ).pack(
            side=tk.LEFT,
            padx=3,
        )

    def add_entry(self, parent, label, variable, row, width):
        tk.Label(
            parent,
            text=label,
            bg=COLORS["card_bg"],
            fg=COLORS["text"],
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=(4, 2),
        )

        entry = tk.Entry(
            parent,
            textvariable=variable,
            width=width,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        entry.grid(
            row=row + 1,
            column=0,
            sticky="ew",
            pady=(0, 6),
        )

        self.entries.append(entry)
        return entry

    def get_page_settings(self):
        settings = self.read_page_settings()
        self.apply_page_settings(settings)
        return settings

    def read_page_settings(self):
        return {
            "page_width_mm": self.get_float(
                self.width_var,
                20.0,
            ),
            "page_height_mm": self.get_float(
                self.height_var,
                20.0,
            ),
            "margin_mm": self.get_float(
                self.margin_var,
                1.5,
            ),
            "code_size_mm": self.get_float(
                self.code_size_var,
                17.0,
            ),
            "horizontal_shift_mm": self.get_float(
                self.horizontal_shift_var,
                -1.0,
                allow_negative=True,
            ),
            "vertical_shift_mm": self.get_float(
                self.vertical_shift_var,
                0.0,
                allow_negative=True,
            ),
        }

    def apply_page_settings(self, settings=None):
        if settings is None:
            settings = self.read_page_settings()

        update_page_settings(
            width_mm=settings["page_width_mm"],
            height_mm=settings["page_height_mm"],
            margin_mm=settings["margin_mm"],
            code_size_mm=settings["code_size_mm"],
            horizontal_shift_mm=settings[
                "horizontal_shift_mm"
            ],
            vertical_shift_mm=settings[
                "vertical_shift_mm"
            ],
        )

    def get_print_settings(self):
        return {
            **self.get_page_settings(),
            "copies": self.get_int(self.copies_var, 1),
            "dpi": self.get_int(self.dpi_var, 300),
        }

    def get_action(self):
        return self.action_var.get().strip()

    def get_printer(self):
        printer = self.printer_var.get().strip()
        return printer or None

    def refresh_printers(self):
        current = self.printer_var.get().strip()
        printers = []

        if win32print:
            try:
                flags = (
                    win32print.PRINTER_ENUM_LOCAL
                    | win32print.PRINTER_ENUM_CONNECTIONS
                )

                records = win32print.EnumPrinters(
                    flags,
                    None,
                    1,
                )

                printers = sorted(
                    {
                        record[2]
                        for record in records
                        if len(record) > 2 and record[2]
                    }
                )
            except Exception:
                pass

        if not current and win32print:
            try:
                current = win32print.GetDefaultPrinter()
            except Exception:
                pass

        self.printer_box["values"] = printers

        if current:
            self.printer_var.set(current)

    def save_profile(self):
        name = self.profile_name_var.get().strip()

        if not name:
            messagebox.showwarning(
                "Профиль",
                "Введите имя профиля.",
                parent=self,
            )
            return

        self.profiles[name] = {
            **self.get_page_settings(),
            "printer": self.get_printer(),
            "copies": self.get_int(self.copies_var, 1),
            "dpi": self.get_int(self.dpi_var, 300),
            "action": self.get_action(),
        }

        self.profile_var.set(name)
        self.refresh_profile_list()
        self.save_settings()

        messagebox.showinfo(
            "Профиль",
            f"Профиль «{name}» сохранён.",
            parent=self,
        )

    def delete_profile(self):
        name = self.profile_var.get().strip()

        if not name or name not in self.profiles:
            messagebox.showwarning(
                "Профиль",
                "Выберите профиль.",
                parent=self,
            )
            return

        if messagebox.askyesno(
            "Удаление",
            f"Удалить профиль «{name}»?",
            parent=self,
        ):
            del self.profiles[name]

            self.profile_var.set("")
            self.profile_name_var.set("")

            self.refresh_profile_list()
            self.save_settings()

    def on_profile_selected(self, event=None):
        """Применяет параметры выбранного профиля."""
        name = self.profile_var.get().strip()
        profile = self.profiles.get(name)

        if not profile:
            return

        self.apply_profile(profile)
        self.profile_name_var.set(name)
        self.save_settings()

    def apply_profile(self, profile):
        self.width_var.set(
            str(profile.get("page_width_mm", 20.0))
        )
        self.height_var.set(
            str(profile.get("page_height_mm", 20.0))
        )
        self.margin_var.set(
            str(profile.get("margin_mm", 1.5))
        )
        self.code_size_var.set(
            str(profile.get("code_size_mm", 17.0))
        )
        self.horizontal_shift_var.set(
            str(profile.get("horizontal_shift_mm", -1.0))
        )
        self.vertical_shift_var.set(
            str(profile.get("vertical_shift_mm", 0.0))
        )

        self.printer_var.set(
            profile.get("printer", "") or ""
        )
        self.copies_var.set(
            str(profile.get("copies", 1))
        )
        self.dpi_var.set(
            str(profile.get("dpi", 300))
        )

        action = profile.get("action", "")

        if action not in {
            "",
            "none",
            "open",
            "print",
            "excel",
            "preview",
        }:
            action = ""

        self.action_var.set(action)
        self.update_action_buttons()

        if action == "preview":
            self.preview_btn.config(
                bg=COLORS["accent"],
                fg="white",
                relief=tk.SUNKEN,
            )
        else:
            self.preview_btn.config(
                bg="#f0f0f0",
                fg=COLORS["text"],
                relief=tk.RAISED,
            )

        self.apply_page_settings()

    def refresh_profile_list(self):
        names = sorted(self.profiles.keys())

        self.profile_box["values"] = names

        current = self.profile_var.get()

        if current and current in self.profiles:
            self.profile_var.set(current)
        elif names:
            self.profile_var.set(names[0])
        else:
            self.profile_var.set("")

    def save_settings(self):
        """Сохраняет текущие настройки, включая пустое действие."""
        data = {
            "page": self.get_page_settings(),
            "printer": self.get_printer(),
            "copies": self.get_int(self.copies_var, 1),
            "dpi": self.get_int(self.dpi_var, 300),
            "action": self.get_action(),
            "active_profile": self.profile_var.get().strip(),
            "page_presets": self.profiles,
        }

        try:
            self.settings_file.write_text(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError as error:
            messagebox.showerror(
                "Ошибка сохранения",
                str(error),
                parent=self,
            )

    def load_settings(self):
        if not self.settings_file.exists():
            return

        try:
            data = json.loads(
                self.settings_file.read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, ValueError, TypeError):
            return

        if isinstance(data.get("page_presets"), dict):
            self.profiles = data["page_presets"]

        self.apply_profile(
            {
                **DEFAULT_PAGE_SETTINGS,
                **data.get("page", {}),
                "printer": data.get("printer", ""),
                "copies": data.get("copies", 1),
                "dpi": data.get("dpi", 300),
                "action": data.get("action", ""),
            }
        )

        self.refresh_profile_list()

        active_profile = data.get("active_profile", "")

        if active_profile in self.profiles:
            self.profile_var.set(active_profile)

    def reset_page_settings(self):
        self.width_var.set("20.0")
        self.height_var.set("20.0")
        self.margin_var.set("1.5")
        self.code_size_var.set("17.0")
        self.horizontal_shift_var.set("-1.0")
        self.vertical_shift_var.set("0.0")

        self.apply_page_settings()
        self.save_settings()

    def set_enabled(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED

        for widget in self.entries:
            try:
                widget.config(state=state)
            except tk.TclError:
                pass

        for widget in (
            self.profile_name_entry,
            self.profile_box,
            self.printer_box,
            self.copies_entry,
            self.dpi_entry,
            self.preview_btn,
        ):
            try:
                widget.config(state=state)
            except tk.TclError:
                pass

        for button in self.action_buttons.values():
            try:
                button.config(state=state)
            except tk.TclError:
                pass

    @staticmethod
    def get_float(variable, default, allow_negative=False):
        try:
            value = float(variable.get())

            if allow_negative or value >= 0:
                return value

            return default

        except (TypeError, ValueError):
            return default

    @staticmethod
    def get_int(variable, default):
        try:
            value = int(variable.get())
            return value if value >= 1 else default

        except (TypeError, ValueError):
            return default