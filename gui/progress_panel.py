import tkinter as tk
from tkinter import ttk


class ProgressPanel(tk.LabelFrame):
    def __init__(
        self,
        master,
    ):
        super().__init__(
            master,
            text="📊 Прогресс",
            bg="#ffffff",
            fg="#2c3e50",
            padx=10,
            pady=10,
        )

        self.progress_var = tk.DoubleVar(
            value=0.0
        )

        self.build_interface()

    def build_interface(self):
        self.columnconfigure(0, weight=1)

        row = 0

        # Прогресс-бар
        self.progress_bar = ttk.Progressbar(
            self,
            variable=self.progress_var,
            maximum=100.0,
            mode="determinate",
        )
        self.progress_bar.grid(
            row=row,
            column=0,
            sticky="ew",
            pady=5,
        )

        row += 1

        # Статистика
        stats_frame = tk.Frame(
            self,
            bg="#ffffff",
        )
        stats_frame.grid(
            row=row,
            column=0,
            sticky="ew",
            pady=5,
        )

        self.file_label = tk.Label(
            stats_frame,
            text="Файл: —",
            bg="#ffffff",
            fg="#2c3e50",
            anchor=tk.W,
            font=("Arial", 9, "bold"),
        )
        self.file_label.pack(
            anchor=tk.W,
            pady=2,
        )

        self.time_label = tk.Label(
            stats_frame,
            text="Время: 0 сек",
            bg="#ffffff",
            fg="#6c757d",
            anchor=tk.W,
        )
        self.time_label.pack(
            anchor=tk.W,
            pady=2,
        )

        self.report_label = tk.Label(
            stats_frame,
            text="Отчёт: —",
            bg="#ffffff",
            fg="#6c757d",
            anchor=tk.W,
        )
        self.report_label.pack(
            anchor=tk.W,
            pady=2,
        )

    def set_stage(self, stage_text):
        """Устанавливает текст стадии обработки"""
        self.file_label.config(text=f"Стадия: {stage_text}")

    def reset(self):
        """Сбрасывает прогресс бар и счётчики"""
        self.progress_var.set(0.0)
        self.file_label.config(text="Файл: —")
        self.time_label.config(text="Время: 0 сек")
        self.report_label.config(text="Отчёт: —")

    def set_progress(
        self,
        value,
    ):
        self.progress_var.set(
            value
        )

    def set_file(
        self,
        current,
        total,
        file_name,
    ):
        self.file_label.config(
            text=f"Файл: {file_name} ({current}/{total})"
        )

    def set_time(
        self,
        time_text,
    ):
        self.time_label.config(
            text=f"Время: {time_text}"
        )

    def set_report(
        self,
        report_text,
    ):
        self.report_label.config(
            text=report_text
        )