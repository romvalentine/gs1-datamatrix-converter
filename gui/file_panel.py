import os
import tkinter as tk
from tkinter import ttk, filedialog

from logger import log


class FilePanel(tk.LabelFrame):
    def __init__(
        self,
        master,
    ):
        super().__init__(
            master,
            bg="#ffffff",
            fg="#2c3e50",
        )

        self.files = []
        self.listbox = None
        self.scrollbar = None
        self.max_height = 150  # Максимальная высота

        self.build_interface()

    def build_interface(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Кнопки
        button_frame = tk.Frame(
            self,
            bg="#ffffff",
        )
        button_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=5,
        )

        tk.Button(
            button_frame,
            text="📁 Добавить файлы",
            command=self.add_files,
            bg="#4a9eff",
            fg="white",
            activebackground="#3a8eef",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
        ).pack(
            side=tk.LEFT,
            padx=5,
        )

        tk.Button(
            button_frame,
            text="🗑 Удалить",
            command=self.remove_selected,
            bg="#dc3545",
            fg="white",
            activebackground="#dc3545",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
        ).pack(
            side=tk.LEFT,
            padx=5,
        )

        tk.Button(
            button_frame,
            text="🗑 Очистить всё",
            command=self.clear_files,
            bg="#6c757d",
            fg="white",
            activebackground="#5a6268",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
        ).pack(
            side=tk.LEFT,
            padx=5,
        )

        # Список файлов
        list_frame = tk.Frame(
            self,
            bg="#ffffff",
        )
        list_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
        )

        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.scrollbar = ttk.Scrollbar(
            list_frame,
            orient=tk.VERTICAL,
        )
        self.scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=self.scrollbar.set,
            bg="#f5f7fa",
            fg="#2c3e50",
            selectbackground="#4a9eff",
            selectforeground="white",
            highlightthickness=0,
            activestyle="none",
            font=("Consolas", 9),
            height=3,  # Начальная высота
        )
        self.listbox.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.scrollbar.config(
            command=self.listbox.yview
        )

        # Статистика
        self.count_label = tk.Label(
            self,
            text="Файлов: 0",
            bg="#ffffff",
            fg="#6c757d",
            anchor=tk.W,
        )
        self.count_label.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=5,
        )

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="Выберите файлы",
            filetypes=[
                (
                    "Все файлы",
                    "*.pdf *.png *.jpg *.jpeg *.gif *.bmp",
                ),
                ("PDF", "*.pdf"),
                ("Изображения", "*.png *.jpg *.jpeg *.gif *.bmp"),
            ],
        )

        for path in paths:
            if path not in self.files:
                self.files.append(path)
                self.listbox.insert(
                    tk.END,
                    os.path.basename(path),
                )

        self.update_height()
        self.update_count()

    def remove_selected(self):
        indices = list(
            self.listbox.curselection()
        )

        for index in reversed(indices):
            self.listbox.delete(index)
            self.files.pop(index)

        self.update_height()
        self.update_count()

    def clear_files(self):
        self.files.clear()
        self.listbox.delete(
            0,
            tk.END,
        )
        self.update_height()
        self.update_count()

    def update_height(self):
        """Обновляет высоту списка файлов"""
        count = len(self.files)
        height = min(count, 10)  # Максимум 10 строк
        self.listbox.config(height=height)

    def update_count(self):
        self.count_label.config(
            text=f"Файлов: {len(self.files)}"
        )

    def get_files(self):
        return list(self.files)

    def set_running(self, running):
        state = (
            tk.DISABLED
            if running
            else tk.NORMAL
        )

        for widget in self.winfo_children():
            if isinstance(
                widget,
                tk.Button,
            ):
                widget.config(
                    state=state
                )