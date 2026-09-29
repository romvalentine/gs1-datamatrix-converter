import tkinter as tk
from tkinter import ttk

from gui.file_panel import FilePanel
from gui.manual_code_panel import ManualCodePanel
from gui.mode_panel import ModePanel
from gui.progress_panel import ProgressPanel
from gui.settings_panel import SettingsPanel


# === Цветовая схема ===
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
    "shadow": "#00000020",
}


class PageRangePanel(tk.LabelFrame):
    def __init__(self, master, on_open_settings=None):
        super().__init__(master, text="📄 Диапазон страниц",
                        bg=COLORS["card_bg"], fg=COLORS["text"],
                        padx=10, pady=10)

        self.range_var = tk.StringVar(value="all")
        self.range_buttons = {}
        self.on_open_settings = on_open_settings

        # Кнопка "Все страницы"
        btn_all = tk.Button(
            self, text="Все страницы",
            command=lambda: self.set_range("all"),
            bg="#f0f0f0", fg="#2c3e50",
            activebackground=COLORS["accent"],
            activeforeground="white",
            relief=tk.RAISED, bd=2,
            width=15, font=("Arial", 9),
        )
        btn_all.grid(row=0, column=0, sticky="w", pady=4)
        self.range_buttons["all"] = btn_all

        # Кнопка "Диапазон"
        btn_range = tk.Button(
            self, text="Диапазон:",
            command=lambda: self.set_range("range"),
            bg="#f0f0f0", fg="#2c3e50",
            activebackground=COLORS["accent"],
            activeforeground="white",
            relief=tk.RAISED, bd=2,
            width=15, font=("Arial", 9),
        )
        btn_range.grid(row=1, column=0, sticky="w", pady=4)
        self.range_buttons["range"] = btn_range

        # Поля ввода
        range_frame = tk.Frame(self, bg=COLORS["card_bg"])
        range_frame.grid(row=1, column=1, sticky="w", padx=10)

        self.from_entry = tk.Entry(range_frame, width=5,
            bg=COLORS["bg"], fg=COLORS["text"],
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"])
        self.from_entry.pack(side=tk.LEFT, padx=4)

        tk.Label(range_frame, text="по", bg=COLORS["card_bg"],
                fg=COLORS["text_muted"]).pack(side=tk.LEFT, padx=4)

        self.to_entry = tk.Entry(range_frame, width=5,
            bg=COLORS["bg"], fg=COLORS["text"],
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"])
        self.to_entry.pack(side=tk.LEFT, padx=4)

        # Кнопка настроек
        if on_open_settings:
            settings_btn = tk.Button(
                self,
                text="⚙ Настройки печати",
                command=on_open_settings,
                bg=COLORS["accent"],
                fg="white",
                activebackground=COLORS["accent_dark"],
                activeforeground="white",
                font=("Arial", 11, "bold"),
                relief=tk.RAISED,
                bd=2,
                cursor="hand2",
                width=22,
                height=2,
            )
            settings_btn.grid(
                row=0,
                column=2,
                rowspan=2,
                sticky="ns",
                padx=(15, 5),
                pady=2,
            )

        self.update_range_buttons()

    def set_range(self, value):
        self.range_var.set(value)
        self.update_range_buttons()

    def update_range_buttons(self):
        current = self.range_var.get()
        for value, btn in self.range_buttons.items():
            if value == current:
                btn.config(bg=COLORS["accent"], fg="white", relief=tk.SUNKEN)
            else:
                btn.config(bg="#f0f0f0", fg="#2c3e50", relief=tk.RAISED)

    def get_range(self):
        if self.range_var.get() == "all":
            return None
        try:
            from_page = int(self.from_entry.get())
            to_page = int(self.to_entry.get())
            if from_page < 1 or to_page < 1 or from_page > to_page:
                return None
            return (from_page, to_page)
        except:
            return None


class AppUI:
    def __init__(self, root, settings_file, on_start, on_stop, on_generate):
        self.root = root
        self.settings_file = settings_file
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_generate = on_generate

        self.mode_panel = None
        self.settings_panel = None
        self.file_panel = None
        self.manual_code_panel = None
        self.progress_panel = None
        self.page_range_panel = None
        self.status_label = None
        self.start_button = None
        self.stop_button = None
        self.preview_button = None

        # Создаём панель настроек (но не показываем)
        self.settings_panel = SettingsPanel(root, settings_file=settings_file)
        self.settings_panel.grid_remove()

        self.configure_root()
        self.build_interface()

    def configure_root(self):
        self.root.configure(bg=COLORS["bg"])
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.root.minsize(1080, 700)
        self.root.geometry("1100x780")

    def build_interface(self):
        # Основной контейнер
        main_container = tk.Frame(self.root, bg=COLORS["bg"])
        main_container.grid(row=0, column=0, sticky="nsew", padx=15, pady=10)
        main_container.columnconfigure(1, weight=1)

        row = 0

        # Верхняя панель: Режим + Диапазон (на одном уровне)
        top_frame = tk.Frame(main_container, bg=COLORS["bg"])
        top_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        top_frame.columnconfigure(0, weight=0)  # Режим
        top_frame.columnconfigure(1, weight=0)  # Диапазон

        # Режим обработки
        mode_frame = tk.Frame(top_frame, bg=COLORS["bg"])
        mode_frame.grid(row=0, column=0, sticky="w", padx=(0, 15))

        self.mode_panel = ModePanel(mode_frame)
        self.mode_panel.pack(anchor=tk.W)

        # Диапазон страниц (справа от режима, на одном уровне)
        self.page_range_panel = PageRangePanel(
            top_frame,
            on_open_settings=self.open_settings,
        )
        self.page_range_panel.grid(
            row=0,
            column=1,
            sticky="e",
        )

        row += 1

        # Кнопки управления
        control_frame = tk.Frame(main_container, bg=COLORS["card_bg"],
                                relief=tk.RAISED, bd=1)
        control_frame.grid(row=row, column=0, pady=8, sticky="ew", ipady=8)
        row += 1

        self.start_button = tk.Button(
            control_frame, text="▶ Запустить обработку",
            command=self.on_start, width=25,
            bg=COLORS["success"], fg="white",
            activebackground=COLORS["success"],
            activeforeground="white",
            font=("Arial", 11, "bold"),
            relief=tk.RAISED, bd=2, cursor="hand2",
        )
        self.start_button.pack(side=tk.LEFT, padx=15)

        self.stop_button = tk.Button(
            control_frame, text="⏹ ОСТАНОВИТЬ",
            command=self.on_stop, width=18,
            state=tk.DISABLED, bg="#999999",
            fg="white", activebackground="#999999",
            activeforeground="white",
            font=("Arial", 11, "bold"),
            relief=tk.RAISED, bd=2, cursor="hand2",
        )
        self.stop_button.pack(side=tk.LEFT, padx=15)

        # Выбор файлов
        file_frame = tk.Frame(main_container, bg=COLORS["card_bg"],
                             relief=tk.RAISED, bd=1)
        file_frame.grid(row=row, column=0, pady=(0, 8), sticky="ew")
        file_frame.columnconfigure(0, weight=1)
        row += 1

        tk.Label(file_frame, text="📁 Файлы для обработки",
                font=("Arial", 11, "bold"),
                bg=COLORS["card_bg"], fg=COLORS["text"]
        ).grid(row=0, column=0, sticky="w", padx=15, pady=10)

        self.file_panel = FilePanel(file_frame)
        self.file_panel.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")

        # Ручной ввод
        manual_frame = tk.Frame(main_container, bg=COLORS["card_bg"],
                               relief=tk.RAISED, bd=1)
        manual_frame.grid(row=row, column=0, pady=(0, 8), sticky="ew")
        row += 1
        manual_frame.columnconfigure(0, weight=1)

        self.manual_code_panel = ManualCodePanel(
            manual_frame,
            on_generate=self.on_generate,
        )
        self.manual_code_panel.grid(
            row=0, column=0, padx=15, pady=(0, 15), sticky="ew")

        # Прогресс
        progress_frame = tk.Frame(main_container, bg=COLORS["card_bg"],
                                 relief=tk.RAISED, bd=1)
        progress_frame.grid(row=row, column=0, pady=(0, 8), sticky="ew")
        row += 1
        progress_frame.columnconfigure(0, weight=1)

        self.progress_panel = ProgressPanel(progress_frame)
        self.progress_panel.grid(
            row=0, column=0, padx=15, pady=(0, 15), sticky="ew")

        # Статус
        self.status_label = tk.Label(
            main_container,
            text="○ Ожидание файлов",
            fg="white",
            bg=COLORS["accent"],
            anchor=tk.W,
            font=("Arial", 10, "bold"),
            relief=tk.RAISED,
            bd=1,
            padx=15,
            pady=8,
        )
        self.status_label.grid(
            row=row,
            column=0,
            pady=(2, 0),
            sticky="ew",
        )

    def open_settings(self):
        self.settings_panel.open_in_window(self.root)

    def set_status(self, text, color="gray"):
        color_map = {"gray": "white", "green": "white",
                    "darkorange": "white", "red": "white"}
        bg_map = {"gray": COLORS["accent"], "green": COLORS["success"],
                 "darkorange": COLORS["warning"], "red": COLORS["danger"]}
        self.status_label.config(
            text=text,
            fg=color_map.get(color, "white"),
            bg=bg_map.get(color, COLORS["accent"]),
        )

    def set_running(self, running):
        self.file_panel.set_running(running)
        self.manual_code_panel.set_enabled(not running)
        self.start_button.config(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_button.config(
            state=tk.NORMAL if running else tk.DISABLED,
            bg=COLORS["danger"] if running else "#999999",
            fg="white",
        )