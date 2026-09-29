import io
import threading
import tkinter as tk

from pathlib import Path
from tkinter import messagebox

import fitz
from PIL import Image, ImageTk

from config import (
    MEMORY_FILE,
    PDF_EXTS,
    SETTINGS_FILE,
)

from core.file_scanner import FileScanner
from core.memory import VariantMemory
from core.stop_control import StopController

from gui.app_ui import AppUI
from gui.app_conversion import ConversionMixin
from gui.app_errors import ErrorHandlingMixin

from services.printing_service import open_pdf, print_pdf


class DataMatrixApp(ConversionMixin, ErrorHandlingMixin):
    """Главный класс приложения."""

    def __init__(self, root):
        self.root = root
        self.root.title("DataMatrix Конвертер")
        self.root.geometry("1100x780")
        self.root.minsize(1080, 700)
        self.root.resizable(True, True)

        self.worker_thread = None
        self.stop_controller = StopController()
        self.memory = VariantMemory(MEMORY_FILE)
        self.scanner = FileScanner(self.memory)

        self.current_file_index = 0
        self.total_files = 0
        self.recognized_count = 0

        self.after_action = ""
        self.selected_printer = None
        self.print_settings = {}
        self.forced_mode = None
        self.error_pages = None

        self.ui = AppUI(
            root,
            settings_file=SETTINGS_FILE,
            on_start=self.start_conversion,
            on_stop=self.stop_conversion,
            on_generate=self.generate_from_text,
        )

        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def ui_callback(self, callback):
        self.root.after(0, callback)

    def resolve_mode(self, file_path):
        if self.forced_mode:
            return self.forced_mode

        mode = self.ui.mode_panel.get_mode()

        if mode != "auto":
            return mode

        extension = Path(file_path).suffix.lower()

        if extension in PDF_EXTS:
            return "multi"

        return "fast"

    def start_conversion(self):
        if (
            self.worker_thread is not None
            and self.worker_thread.is_alive()
        ):
            return

        files = self.ui.file_panel.get_files()

        if not files:
            messagebox.showwarning(
                "Внимание",
                "Выберите хотя бы один файл.",
                parent=self.root,
            )
            return

        # Настройки из окна сохраняются в JSON при закрытии.
        # Поэтому перед обработкой перечитываем их в основную панель.
        self.ui.settings_panel.load_settings()
        settings_panel = self.ui.settings_panel

        self.after_action = settings_panel.get_action()
        self.selected_printer = settings_panel.get_printer()
        self.print_settings = settings_panel.get_print_settings()

        if not self.after_action:
            messagebox.showwarning(
                "Настройки печати",
                "Выберите действие после обработки:\n\n"
                "• Ничего\n"
                "• Открыть\n"
                "• Печать\n"
                "• Excel\n"
                "• Предпросмотр",
                parent=self.root,
            )
            return

        self.stop_controller.reset()
        self.total_files = len(files)
        self.current_file_index = 0
        self.recognized_count = 0

        self.ui.progress_panel.reset()
        self.ui.set_running(True)
        self.ui.set_status("⏳ Обработка файлов...", "gray")

        self.worker_thread = threading.Thread(
            target=self.run_conversion,
            daemon=True,
        )
        self.worker_thread.start()

    def stop_conversion(self):
        if (
            self.worker_thread is None
            or not self.worker_thread.is_alive()
        ):
            return

        self.stop_controller.stop()
        self.ui.set_status(
            "⏹ Остановка после текущей операции...",
            "darkorange",
        )

    def progress_callback(
        self,
        stage="",
        current=0,
        total=0,
        label="",
    ):
        if stage == "decode":
            self.ui_callback(
                lambda label=label: self.ui.progress_panel.set_stage(
                    "Распознавание: " + label
                )
            )

        elif stage == "frame":
            self.ui_callback(
                lambda label=label: self.ui.progress_panel.set_stage(label)
            )

        elif stage == "page":
            self.ui_callback(
                lambda current=current, total=total: self.ui.progress_panel.set_file(
                    current,
                    total,
                    f"Страница {current}",
                )
            )

        if total:
            completed = self.current_file_index - 1 + current / total
            value = completed / max(1, self.total_files) * 100

            self.ui_callback(
                lambda value=value: self.ui.progress_panel.set_progress(value)
            )

    def apply_after_action(self, output_path, codes=None):
        """Выполняет действие, выбранное после генерации PDF."""
        from logger import log

        log(f"apply_after_action: after_action={self.after_action!r}")

        output_path = Path(output_path)

        if not output_path.exists():
            log(f"apply_after_action: PDF not found: {output_path}")
            return

        try:
            if self.after_action == "none":
                self.ui_callback(
                    lambda: self.ui.set_status(
                        "✅ PDF создан без дополнительного действия",
                        "green",
                    )
                )
                return

            if self.after_action == "preview":
                return

            if self.after_action == "open":
                open_pdf(output_path)
                self.ui_callback(
                    lambda: self.ui.set_status("✅ PDF открыт", "green")
                )
                return

            if self.after_action == "print":
                print_pdf(
                    output_path,
                    self.selected_printer,
                    self.print_settings,
                )

                printer = self.selected_printer or "по умолчанию"

                self.ui_callback(
                    lambda: self.ui.set_status(
                        f"🖨 PDF отправлен на печать: {printer}",
                        "green",
                    )
                )
                return

            if self.after_action == "excel":
                from core.pdf_to_excel import extract_codes_from_pdf

                excel_path = output_path.with_suffix(".xlsx")

                extract_codes_from_pdf(
                    str(output_path),
                    codes or [],
                    str(excel_path),
                )

                self.ui_callback(
                    lambda: self.ui.set_status(
                        f"📊 Коды экспортированы в Excel: {excel_path.name}",
                        "green",
                    )
                )

        except Exception as error:
            log(f"after action error: {error}")

            self.ui_callback(
                lambda error=error: messagebox.showwarning(
                    "Дополнительное действие",
                    str(error),
                    parent=self.root,
                )
            )

    def show_preview_window(self, pdf_path, codes):
        """
        Показывает первую страницу сгенерированного PDF как изображение.
        PDF не открывается во внешней программе и не отправляется на печать.
        """
        result = {
            "continue": True,
        }
        finished = threading.Event()

        def create_window():
            try:
                document = fitz.open(str(pdf_path))
                page = document[0]

                pixmap = page.get_pixmap(
                    matrix=fitz.Matrix(8, 8),
                    alpha=False,
                )

                image = Image.open(
                    io.BytesIO(pixmap.tobytes("png"))
                ).convert("RGB")

                document.close()

                max_size = 420
                image.thumbnail(
                    (max_size, max_size),
                    Image.Resampling.NEAREST,
                )

                preview = tk.Toplevel(self.root)
                preview.title("👁 Предпросмотр DataMatrix")
                preview.configure(bg="#f5f7fa")
                preview.resizable(False, False)
                preview.transient(self.root)
                preview.grab_set()

                tk.Label(
                    preview,
                    text="Предпросмотр сгенерированного DataMatrix",
                    bg="#f5f7fa",
                    fg="#2c3e50",
                    font=("Arial", 12, "bold"),
                ).pack(padx=20, pady=(15, 5))

                tk.Label(
                    preview,
                    text=f"Найдено кодов: {len(codes)}",
                    bg="#f5f7fa",
                    fg="#6c757d",
                    font=("Arial", 9),
                ).pack(pady=(0, 10))

                photo = ImageTk.PhotoImage(image)

                image_label = tk.Label(
                    preview,
                    image=photo,
                    bg="white",
                    relief=tk.RAISED,
                    bd=1,
                )
                image_label.image = photo
                image_label.pack(padx=25, pady=5)

                tk.Label(
                    preview,
                    text="Продолжить поиск и обработку?",
                    bg="#f5f7fa",
                    fg="#2c3e50",
                    font=("Arial", 10),
                ).pack(pady=(12, 8))

                button_frame = tk.Frame(preview, bg="#f5f7fa")
                button_frame.pack(pady=(0, 15))

                def continue_processing():
                    result["continue"] = True
                    preview.destroy()

                def stop_processing():
                    result["continue"] = False
                    preview.destroy()

                tk.Button(
                    button_frame,
                    text="▶ Продолжить",
                    command=continue_processing,
                    width=17,
                    bg="#28a745",
                    fg="white",
                    activebackground="#28a745",
                    activeforeground="white",
                    relief=tk.RAISED,
                    bd=2,
                    font=("Arial", 10, "bold"),
                ).pack(side=tk.LEFT, padx=6)

                tk.Button(
                    button_frame,
                    text="⏹ Остановить",
                    command=stop_processing,
                    width=17,
                    bg="#dc3545",
                    fg="white",
                    activebackground="#dc3545",
                    activeforeground="white",
                    relief=tk.RAISED,
                    bd=2,
                    font=("Arial", 10, "bold"),
                ).pack(side=tk.LEFT, padx=6)

                preview.protocol(
                    "WM_DELETE_WINDOW",
                    continue_processing,
                )

                def on_destroy(event):
                    if event.widget is preview:
                        finished.set()

                preview.bind("<Destroy>", on_destroy)

            except Exception as error:
                messagebox.showerror(
                    "Ошибка предпросмотра",
                    f"Не удалось отобразить сгенерированный код:\n{error}",
                    parent=self.root,
                )
                finished.set()

        # Tkinter-виджеты должны создаваться только в основном потоке.
        self.root.after(0, create_window)

        # Поток обработки ждёт ответа пользователя.
        finished.wait()

        if result["continue"]:
            self.ui_callback(
                lambda: self.ui.set_status(
                    "👁 Предпросмотр подтверждён — обработка продолжается",
                    "green",
                )
            )
        else:
            self.stop_controller.stop()

            self.ui_callback(
                lambda: self.ui.set_status(
                    "⏹ Обработка остановлена после предпросмотра",
                    "darkorange",
                )
            )

    def generate_from_text(self, codes, action):
        from logger import log

        log(f"generate_from_text RECEIVED codes: {codes!r}")

        if not codes:
            messagebox.showwarning(
                "Ручной ввод",
                "Введите хотя бы один код.",
                parent=self.root,
            )
            return

        normalized_codes = [
            c.replace("<GS>", "\x1d")
            for c in codes
        ]

        self.ui.settings_panel.load_settings()
        self.selected_printer = self.ui.settings_panel.get_printer()
        self.print_settings = self.ui.settings_panel.get_print_settings()

        try:
            from services.pdf_service import create_pdf_from_codes

            result = create_pdf_from_codes(codes=normalized_codes)

        except Exception as error:
            log(f"manual PDF generation error: {error}")

            messagebox.showerror(
                "Ошибка генерации",
                f"Не удалось создать PDF из текста:\n{error}",
                parent=self.root,
            )
            return

        from services.pdf_service import get_output_path

        pdf_path = get_output_path(result)

        if pdf_path is None:
            messagebox.showerror(
                "Ошибка генерации",
                "PDF не был создан.\n\nПроверьте журнал приложения.",
                parent=self.root,
            )
            return

        try:
            if action == "open":
                open_pdf(pdf_path)

                self.ui.set_status(
                    "✅ PDF из ручного ввода создан и открыт",
                    "green",
                )

            elif action == "print":
                print_pdf(
                    pdf_path,
                    self.selected_printer,
                    self.print_settings,
                )

                printer = self.selected_printer or "по умолчанию"

                self.ui.set_status(
                    f"🖨 PDF из ручного ввода отправлен на печать: {printer}",
                    "green",
                )

        except Exception as error:
            log(f"manual PDF action error: {error}")

            messagebox.showerror(
                "Ошибка открытия или печати",
                str(error),
                parent=self.root,
            )
            return

        messagebox.showinfo(
            "Готово",
            f"Создан PDF из {len(normalized_codes)} код(ов).",
            parent=self.root,
        )

    def close(self):
        if (
            self.worker_thread is not None
            and self.worker_thread.is_alive()
        ):
            self.stop_controller.stop()

            self.ui.set_status(
                "Сначала завершается текущая обработка...",
                "darkorange",
            )
            return

        self.root.destroy()

    def run(self):
        self.root.mainloop()