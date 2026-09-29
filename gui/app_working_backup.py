import os
import threading
import time
import tkinter as tk

from pathlib import Path
from tkinter import messagebox

from config import (
    MEMORY_FILE,
    PDF_EXTS,
    SETTINGS_FILE,
)

from core.file_scanner import FileScanner
from core.memory import VariantMemory
from core.models import ScanResult
from core.reports import save_scan_report
from core.stop_control import StopController

from gui.file_panel import FilePanel
from gui.mode_panel import ModePanel
from gui.progress_panel import ProgressPanel
from gui.settings_panel import SettingsPanel

from logger import format_seconds, log

from pdf.generator import (
    generate_pdf_with_codes,
)

from services.printing_service import (
    open_pdf,
    print_pdf,
)

class DataMatrixApp:
    def __init__(
        self,
        root,
    ):
        self.root = root

        self.root.title(
            "DataMatrix Конвертер"
        )

        self.root.geometry(
            "900x760"
        )

        self.root.minsize(
            760,
            620,
        )

        self.root.columnconfigure(
            0,
            weight=1,
        )

        self.root.rowconfigure(
            4,
            weight=1,
        )

        self.worker_thread = None

        self.stop_controller = (
            StopController()
        )

        self.memory = VariantMemory(
            MEMORY_FILE
        )

        self.scanner = FileScanner(
            self.memory
        )

        self.current_file_index = 0
        self.total_files = 0
        self.recognized_count = 0
        self.after_action = "none"
        self.selected_printer = None
        self.print_settings = {}

        tk.Label(
            root,
            text="📄 DataMatrix Конвертер",
            font=(
                "Arial",
                16,
                "bold",
            ),
        ).grid(
            row=0,
            column=0,
            pady=10,
        )

        self.mode_panel = ModePanel(
            root
        )

        self.mode_panel.grid(
            row=1,
            column=0,
            padx=15,
            pady=4,
            sticky="ew",
        )

        self.settings_panel = (
            SettingsPanel(
                root,
                SETTINGS_FILE,
            )
        )

        self.settings_panel.grid(
            row=2,
            column=0,
            padx=15,
            pady=4,
            sticky="ew",
        )

        control_frame = tk.Frame(
            root
        )

        control_frame.grid(
            row=3,
            column=0,
            pady=6,
        )

        self.start_button = tk.Button(
            control_frame,
            text="▶ Запустить обработку",
            command=self.start_conversion,
            width=22,
        )

        self.start_button.pack(
            side=tk.LEFT,
            padx=5,
        )

        self.stop_button = tk.Button(
            control_frame,
            text="⏹ Остановить",
            command=self.stop_conversion,
            width=18,
            state=tk.DISABLED,
        )

        self.stop_button.pack(
            side=tk.LEFT,
            padx=5,
        )

        self.file_panel = FilePanel(
            root
        )

        self.file_panel.grid(
            row=4,
            column=0,
            padx=15,
            pady=5,
            sticky="nsew",
        )

        self.progress_panel = (
            ProgressPanel(root)
        )

        self.progress_panel.grid(
            row=5,
            column=0,
            padx=15,
            pady=5,
            sticky="ew",
        )

        self.status_label = tk.Label(
            root,
            text="Выберите файлы",
            fg="gray",
            anchor=tk.W,
        )

        self.status_label.grid(
            row=6,
            column=0,
            padx=18,
            pady=2,
            sticky="ew",
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close,
        )

    def ui(
        self,
        callback,
    ):
        self.root.after(
            0,
            callback,
        )

    def resolve_mode(
        self,
        file_path,
    ):
        mode = self.mode_panel.get_mode()

        if mode != "auto":
            return mode

        extension = Path(
            file_path
        ).suffix.lower()

        if extension in PDF_EXTS:
            return "multi"

        return "fast"

    def set_running(
        self,
        running,
    ):
        self.file_panel.set_running(
            running
        )

        self.settings_panel.set_enabled(
            not running
        )

        self.start_button.config(
            state=(
                tk.DISABLED
                if running
                else tk.NORMAL
            )
        )

        self.stop_button.config(
            state=(
                tk.NORMAL
                if running
                else tk.DISABLED
            )
        )

    def start_conversion(self):
        if (
            self.worker_thread is not None
            and self.worker_thread.is_alive()
        ):
            return

        files = self.file_panel.get_files()

        if not files:
            messagebox.showwarning(
                "Внимание",
                "Выберите хотя бы один файл.",
            )

            return

        self.stop_controller.reset()

        self.total_files = len(
            files
        )

        self.current_file_index = 0
        self.recognized_count = 0

        self.after_action = (
            self.settings_panel.get_action()
        )

        self.selected_printer = (
            self.settings_panel.get_printer()
        )

        self.print_settings = (
            self.settings_panel
            .get_print_settings()
        )

        self.progress_panel.reset()

        self.set_running(
            True
        )

        self.worker_thread = (
            threading.Thread(
                target=self.run_conversion,
                daemon=True,
            )
        )

        self.worker_thread.start()

    def stop_conversion(self):
        if (
            self.worker_thread is None
            or not self.worker_thread.is_alive()
        ):
            return

        self.stop_controller.stop()

        self.status_label.config(
            text=(
                "⏹ Остановка после "
                "текущего decode..."
            ),
            fg="darkorange",
        )

    def progress_callback(
        self,
        stage="",
        current=0,
        total=0,
        label="",
    ):
        if stage == "page":
            self.ui(
                lambda:
                self.progress_panel.set_page(
                    current,
                    total,
                )
            )

            if total:
                completed = (
                    self.current_file_index
                    - 1
                    + current / total
                )

                value = (
                    completed
                    / max(
                        1,
                        self.total_files,
                    )
                    * 100
                )

                self.ui(
                    lambda value=value:
                    self.progress_panel
                    .set_progress(
                        value
                    )
                )

        if stage == "decode":
            text = (
                "распознавание — "
                f"{label}"
            )

            self.ui(
                lambda text=text:
                self.progress_panel
                .set_stage(text)
            )

        elif stage == "frame":
            self.ui(
                lambda label=label:
                self.progress_panel
                .set_stage(label)
            )


    def apply_after_action(
        self,
        output_path,
    ):
        if not output_path.exists():
            return

        try:
            if self.after_action == "open":
                open_pdf(
                    output_path
                )

                self.ui(
                    lambda:
                    self.status_label.config(
                        text="PDF открыт после обработки",
                        fg="green",
                    )
                )

            elif self.after_action == "print":
                print_pdf(
                    output_path,
                    self.selected_printer,
                    self.print_settings,
                )

                printer_text = (
                    self.selected_printer
                    or "по умолчанию"
                )

                self.ui(
                    lambda printer_text=(
                        printer_text
                    ):
                    self.status_label.config(
                        text=(
                            "PDF отправлен на печать: "
                            f"{printer_text}"
                        ),
                        fg="green",
                    )
                )

        except Exception as error:
            log(
                f"after action error: "
                f"{error}"
            )

            self.ui(
                lambda error=error:
                messagebox.showwarning(
                    "Дополнительное действие",
                    str(error),
                )
            )

    def run_conversion(self):
        started_at = time.perf_counter()

        files = self.file_panel.get_files()

        all_codes = []
        scan_results = []
        errors = []

        try:
            first_file = Path(
                files[0]
            )

            output_path = (
                first_file.parent
                / (
                    first_file.stem
                    + " (все коды).pdf"
                )
            )

            for index, file_path in enumerate(
                files,
                start=1,
            ):
                if self.stop_controller.is_stopped():
                    break

                self.current_file_index = index

                file_name = os.path.basename(
                    file_path
                )

                mode = self.resolve_mode(
                    file_path
                )

                file_started = (
                    time.perf_counter()
                )

                self.ui(
                    lambda index=index,
                    file_name=file_name:
                    self.progress_panel.set_file(
                        index,
                        self.total_files,
                        file_name,
                    )
                )

                try:
                    codes = self.scanner.scan(
                        file_path,
                        mode=mode,
                        progress_callback=(
                            self.progress_callback
                        ),
                        stop_event=(
                            self.stop_controller.event
                        ),
                    )

                    elapsed = (
                        time.perf_counter()
                        - file_started
                    )

                    all_codes.extend(
                        codes
                    )

                    count = sum(
                        code is not None
                        for code in codes
                    )

                    self.recognized_count += count

                    self.ui(
                        lambda:
                        self.progress_panel.set_found(
                            self.recognized_count
                        )
                    )

                    status = (
                        "stopped"
                        if self.stop_controller.is_stopped()
                        else (
                            "ok"
                            if count > 0
                            else "not_found"
                        )
                    )

                    scan_results.append(
                        ScanResult(
                            file_path=str(
                                file_path
                            ),
                            codes_count=count,
                            elapsed=elapsed,
                            mode=mode,
                            status=status,
                        )
                    )

                except Exception as error:
                    elapsed = (
                        time.perf_counter()
                        - file_started
                    )

                    log(
                        f"file error: "
                        f"{file_name}: "
                        f"{error}"
                    )

                    errors.append(
                        f"{file_name}: {error}"
                    )

                    scan_results.append(
                        ScanResult(
                            file_path=str(
                                file_path
                            ),
                            codes_count=0,
                            elapsed=elapsed,
                            mode=mode,
                            status="error",
                            error=str(error),
                        )
                    )

                    all_codes.append(None)

            self.memory.save_if_changed()

            total_elapsed = (
                time.perf_counter()
                - started_at
            )

            created_count = 0

            if all_codes:
                settings = self.print_settings

                _, created_count = (
                    generate_pdf_with_codes(
                        all_codes,
                        str(output_path),
                        page_width_mm=settings.get(
                            "label_width_mm",
                            25.4,
                        ),
                        page_height_mm=settings.get(
                            "label_height_mm",
                            20.4,
                        ),
                        margin_mm=0.0,
                        code_size_mm=settings.get(
                            "code_size_mm",
                            17.0,
                        ),
                    )
                )

            stopped = (
                self.stop_controller.is_stopped()
            )

            if all_codes and not stopped:
                self.apply_after_action(
                    output_path
                )

            report_path = save_scan_report(
                scan_results
            )

            self.ui(
                lambda:
                self.progress_panel.set_progress(
                    100
                )
            )

            self.ui(
                lambda:
                self.progress_panel.set_time(
                    format_seconds(
                        total_elapsed
                    )
                )
            )

            self.ui(
                lambda:
                self.progress_panel.set_report(
                    f"Отчёт сохранён: "
                    f"{report_path}"
                )
            )

            result_text = (
                "⏹ Остановлено"
                if stopped
                else (
                    "✅ Завершено. "
                    f"Кодов: "
                    f"{self.recognized_count}"
                )
            )

            self.ui(
                lambda text=result_text:
                self.status_label.config(
                    text=text,
                    fg=(
                        "darkorange"
                        if stopped
                        else "green"
                    ),
                )
            )

            message = (
                (
                    "Обработка остановлена."
                    if stopped
                    else "Обработка завершена."
                )
                + "\n\n"
                f"Найдено кодов: "
                f"{self.recognized_count}\n"
                f"Создано кодов: "
                f"{created_count}\n"
                f"Время: "
                f"{format_seconds(total_elapsed)}\n\n"
                f"PDF:\n{output_path}\n\n"
                f"Отчёт:\n{report_path}"
            )

            if errors:
                message += (
                    "\n\nОшибки:\n"
                    + "\n".join(errors)
                )

            self.ui(
                lambda message=message:
                messagebox.showinfo(
                    "Результат",
                    message,
                )
            )

        except Exception as error:
            log(
                f"conversion error: "
                f"{error}"
            )

            self.ui(
                lambda error=error:
                messagebox.showerror(
                    "Ошибка",
                    str(error),
                )
            )

        finally:
            self.memory.save_if_changed()

            self.ui(
                lambda:
                self.set_running(
                    False
                )
            )

    def close(self):
        if (
            self.worker_thread is not None
            and self.worker_thread.is_alive()
        ):
            self.stop_controller.stop()

            self.status_label.config(
                text=(
                    "Сначала завершается "
                    "текущая обработка..."
                ),
                fg="darkorange",
            )

            return

        self.root.destroy()

    def run(self):
        self.root.mainloop()