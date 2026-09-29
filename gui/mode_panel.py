import tkinter as tk
from tkinter import ttk

from config import DEFAULT_MODE


# Цветовая схема
COLORS = {
    "bg": "#f5f7fa",
    "card_bg": "#ffffff",
    "accent": "#4a9eff",
    "accent_dark": "#3a8eef",
    "success": "#28a745",
    "success_bg": "#e8f5e9",
    "danger": "#dc3545",
    "danger_bg": "#fde8e8",
    "warning": "#ffc107",
    "text": "#2c3e50",
    "text_muted": "#6c757d",
    "border": "#e1e5eb",
}


class ModePanel(tk.LabelFrame):
    def __init__(
        self,
        master,
    ):
        super().__init__(
            master,
            text="⚙ Режим обработки",
            bg="#ffffff",
            fg="#2c3e50",
            padx=10,
            pady=10,
        )

        self.mode_var = tk.StringVar(
            value=DEFAULT_MODE
        )

        self.buttons = {}

        modes = [
            ("🚀 Авто", "auto"),
            ("⚡ Быстро", "fast"),
            ("📑 Несколько", "multi"),
            ("🎯 Точно", "safe"),
            ("📷 Фото", "photo"),
        ]

        # Контейнер для кнопок
        button_frame = tk.Frame(
            self,
            bg="#ffffff",
        )
        button_frame.grid(
            row=0,
            column=0,
            sticky="w",
        )

        # Кнопки-переключатели
        for i, (text, value) in enumerate(modes):
            btn = tk.Button(
                button_frame,
                text=text,
                command=lambda v=value: self.set_mode(v),
                bg="#f0f0f0",
                fg="#2c3e50",
                activebackground=COLORS["accent"],
                activeforeground="white",
                relief=tk.RAISED,
                bd=2,
                width=12,
                font=("Arial", 9),
            )
            btn.grid(
                row=0,
                column=i,
                padx=4,
            )
            self.buttons[value] = btn

        # Описание
        self.description = tk.Label(
            self,
            text="",
            fg="#6c757d",
            bg="#ffffff",
            anchor=tk.W,
            wraplength=400,
        )
        self.description.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(8, 0),
        )

        self.update_description()
        self.update_buttons()

    def set_mode(self, mode):
        self.mode_var.set(mode)
        self.update_buttons()
        self.update_description()

    def update_buttons(self):
        current = self.mode_var.get()
        for value, btn in self.buttons.items():
            if value == current:
                btn.config(
                    bg=COLORS["accent"],
                    fg="white",
                    relief=tk.SUNKEN,
                )
            else:
                btn.config(
                    bg="#f0f0f0",
                    fg="#2c3e50",
                    relief=tk.RAISED,
                )

    def update_description(self):
        descriptions = {
            "auto": "📄 PDF → несколько кодов, 📷 изображения → быстро",
            "fast": "⚡ Быстрые варианты с минимальным временем",
            "multi": "📑 Поиск нескольких DataMatrix на странице",
            "safe": "🎯 Полный поиск с поворотами и вариантами",
            "photo": "📷 Для фото и красного скотча",
        }

        self.description.config(
            text=descriptions.get(
                self.mode_var.get(),
                "",
            )
        )

    def get_mode(self):
        return self.mode_var.get()