import os
import time
import threading
import tkinter as tk

from pathlib import Path

from core.models import ScanResult
from logger import log


class ConversionMixin:
    """Миксин для логики обработки файлов."""

    def run_conversion(self):
        started_at = time.perf_counter()
        files = self.ui.file_panel.get_files()

        all_codes = []
        scan_results = []
        errors = []
        output_path = None
        generation_result = None

        self.original_file_path = Path(files[0]) if files else None
        page_range = self.ui.page_range_panel.get_range()

        if self.error_pages:
            log(
                f"=== Обработка только ошибочных листов: "
                f"{self.error_pages} ==="
            )
            return

        try:
            first_file = Path(files[0])
            output_path = (
                first_file.parent
                / f"{first_file.stem} (все коды).pdf"
            )

            for index, file_path in enumerate(files, start=1):
                if self.stop_controller.is_stopped():
                    break

                self.current_file_index = index

                file_name = os.path.basename(file_path)
                mode = self.resolve_mode(file_path)
                file_started = time.perf_counter()

                self.ui_callback(
                    lambda index=index, file_name=file_name: (
                        self.ui.progress_panel.set_file(
                            index,
                            self.total_files,
                            file_name,
                        )
                    )
                )

                try:
                    codes = self.scanner.scan(
                        file_path,
                        mode=mode,
                        progress_callback=self.progress_callback,
                        stop_event=self.stop_controller.event,
                        page_range=page_range,
                    )

                    codes = list(codes or [])
                    elapsed = time.perf_counter() - file_started

                    scan_results.append(
                        ScanResult(
                            file_path=str(file_path),
                            codes_count=len(codes),
                            elapsed=elapsed,
                            mode=mode,
                            status="success" if codes else "not_found",
                            error=None,
                        )
                    )

                    # Предпросмотр появляется после нахождения кода.
                    # PDF пока НЕ создаётся и не открывается.
                    if codes and self.after_action == "preview":
                        action = self.show_code_preview(
                            codes=codes,
                            file_name=file_name,
                        )

                        # Нажата кнопка «Остановить».
                        if action == "stop":
                            self.stop_controller.stop()
                            break

                        # Код сохраняем в любом случае:
                        # и при «Продолжить поиск», и при «Создать PDF».
                        all_codes.extend(codes)

                        # Нажата кнопка «Создать PDF сейчас».
                        if action in {"generate", "print", "excel"}:
                            from services.pdf_service import create_pdf

                            # При печати и Excel временно меняем действие,
                            # чтобы handle_generation_result выполнил его.
                            original_action = self.after_action

                            if action == "print":
                                self.after_action = "print"
                            elif action == "excel":
                                self.after_action = "excel"
                            else:
                                self.after_action = "none"

                            generation_result = create_pdf(
                                codes=all_codes,
                                output_path=output_path,
                            )

                            log(
                                f"GENERATOR RESULT: "
                                f"{generation_result!r}"
                            )

                            if generation_result:
                                self.handle_generation_result(
                                    generation_result,
                                    output_path,
                                )

                            self.after_action = original_action
                            return

                        # Нажата «Продолжить поиск».
                        # Переходим к следующему файлу.
                        continue

                    # Обычный режим: добавляем все найденные коды.
                    all_codes.extend(codes)

                except Exception as error:
                    elapsed = time.perf_counter() - file_started

                    log(f"file error: {file_name}: {error}")

                    errors.append(
                        f"{file_name}: {error}"
                    )

                    scan_results.append(
                        ScanResult(
                            file_path=str(file_path),
                            codes_count=0,
                            elapsed=elapsed,
                            mode=mode,
                            status="error",
                            error=str(error),
                        )
                    )

                    all_codes.append(None)

            self.memory.save_if_changed()

            stopped = self.stop_controller.is_stopped()

            # Если пользователь не остановил обработку и коды найдены —
            # создаём итоговый PDF.
            if all_codes and output_path and not stopped:
                from services.pdf_service import create_pdf

                generation_result = create_pdf(
                    codes=all_codes,
                    output_path=output_path,
                )

                log(
                    f"GENERATOR RESULT: "
                    f"{generation_result!r}"
                )

            if generation_result is not None and not stopped:
                self.handle_generation_result(
                    generation_result,
                    output_path,
                )

            total_elapsed = time.perf_counter() - started_at

            from core.reports import save_scan_report

            report_path = save_scan_report(scan_results)

            self.ui_callback(
                lambda: self.ui.progress_panel.set_progress(100)
            )

            self.ui_callback(
                lambda: self.ui.progress_panel.set_time(
                    self._format_seconds(total_elapsed)
                )
            )

            self.ui_callback(
                lambda: self.ui.progress_panel.set_report(
                    f"Отчёт сохранён: {report_path}"
                )
            )

            if stopped:
                status_text = "⏹ Остановлено пользователем"

            elif generation_result:
                status_text = (
                    "✅ Обработка завершена. "
                    f"Распознано: "
                    f"{generation_result.get('success_count', 0)}"
                )

            else:
                status_text = "⚠ Коды не найдены"

            self.ui_callback(
                lambda status_text=status_text, stopped=stopped,
                generation_result=generation_result: self.ui.set_status(
                    status_text,
                    (
                        "darkorange"
                        if stopped
                        else "green"
                        if generation_result
                        else "red"
                    ),
                )
            )

            created_count = 0

            if generation_result:
                created_count = generation_result.get(
                    "success_count",
                    0,
                )

            message = (
                (
                    "Обработка остановлена."
                    if stopped
                    else "Обработка завершена."
                )
                + "\n\n"
                f"Найдено кодов: {self.recognized_count}\n"
                f"Создано кодов: {created_count}\n"
                f"Время: {self._format_seconds(total_elapsed)}\n\n"
                f"Отчёт:\n{report_path}"
            )

            if generation_result and output_path:
                message += f"\n\nPDF:\n{output_path}"

            if errors:
                message += (
                    "\n\nОшибки:\n"
                    + "\n".join(errors)
                )

            from tkinter import messagebox

            self.ui_callback(
                lambda message=message: messagebox.showinfo(
                    "Результат",
                    message,
                    parent=self.root,
                )
            )

        except Exception as error:
            log(f"conversion error: {error}")

            from tkinter import messagebox

            self.ui_callback(
                lambda error=error: messagebox.showerror(
                    "Ошибка",
                    str(error),
                    parent=self.root,
                )
            )

        finally:
            self.memory.save_if_changed()
            self.forced_mode = None

            self.ui_callback(
                lambda: self.ui.set_running(False)
            )

    def show_code_preview(self, codes, file_name):
        """
        Показывает все найденные DataMatrix в прокручиваемом окне.

        Возвращает:
        - "continue" — продолжить обработку следующих файлов;
        - "generate" — создать PDF;
        - "print" — создать PDF и напечатать;
        - "excel" — создать Excel;
        - "stop" — остановить обработку.
        """
        from PIL import Image, ImageTk
        from pdf.generator import build_datamatrix_image

        result = {
            "action": "stop",
        }

        dialog_event = threading.Event()

        def show_dialog():
            try:
                dialog = tk.Toplevel(self.root)
                dialog.title("👁 Предпросмотр DataMatrix")
                dialog.configure(bg="#f5f7fa")
                dialog.geometry("620x650")
                dialog.minsize(520, 450)
                dialog.transient(self.root)
                dialog.grab_set()

                tk.Label(
                    dialog,
                    text="✅ Коды найдены",
                    bg="#f5f7fa",
                    fg="#2c3e50",
                    font=("Arial", 13, "bold"),
                ).pack(
                    padx=20,
                    pady=(14, 3),
                )

                tk.Label(
                    dialog,
                    text=(
                        f"Файл: {file_name}\n"
                        f"Найдено кодов: {len(codes)}"
                    ),
                    bg="#f5f7fa",
                    fg="#6c757d",
                    justify="center",
                    font=("Arial", 9),
                ).pack(
                    pady=(0, 10),
                )

                # Контейнер с вертикальной прокруткой.
                canvas_frame = tk.Frame(
                    dialog,
                    bg="#f5f7fa",
                )
                canvas_frame.pack(
                    fill=tk.BOTH,
                    expand=True,
                    padx=15,
                    pady=(0, 10),
                )

                preview_canvas = tk.Canvas(
                    canvas_frame,
                    bg="#ffffff",
                    highlightthickness=1,
                    highlightbackground="#e1e5eb",
                )
                preview_canvas.pack(
                    side=tk.LEFT,
                    fill=tk.BOTH,
                    expand=True,
                )

                scrollbar = tk.Scrollbar(
                    canvas_frame,
                    orient=tk.VERTICAL,
                    command=preview_canvas.yview,
                )
                scrollbar.pack(
                    side=tk.RIGHT,
                    fill=tk.Y,
                )

                preview_canvas.configure(
                    yscrollcommand=scrollbar.set,
                )

                codes_frame = tk.Frame(
                    preview_canvas,
                    bg="#ffffff",
                )

                canvas_window = preview_canvas.create_window(
                    (0, 0),
                    window=codes_frame,
                    anchor="nw",
                )

                # Ссылки на изображения обязательны:
                # иначе ImageTk может удалить изображения из памяти.
                dialog.preview_images = []

                def update_scroll_region(event=None):
                    preview_canvas.configure(
                        scrollregion=preview_canvas.bbox("all")
                    )

                def resize_inner_frame(event):
                    preview_canvas.itemconfigure(
                        canvas_window,
                        width=event.width,
                    )

                codes_frame.bind(
                    "<Configure>",
                    update_scroll_region,
                )

                preview_canvas.bind(
                    "<Configure>",
                    resize_inner_frame,
                )

                # Прокрутка колёсиком мыши.
                def mouse_wheel(event):
                    if event.delta:
                        preview_canvas.yview_scroll(
                            int(-event.delta / 120),
                            "units",
                        )
                    elif event.num == 4:
                        preview_canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        preview_canvas.yview_scroll(1, "units")

                preview_canvas.bind_all(
                    "<MouseWheel>",
                    mouse_wheel,
                )
                preview_canvas.bind_all(
                    "<Button-4>",
                    mouse_wheel,
                )
                preview_canvas.bind_all(
                    "<Button-5>",
                    mouse_wheel,
                )

                # Генерируем изображение каждого найденного кода.
                for index, code in enumerate(codes, start=1):
                    item_frame = tk.Frame(
                        codes_frame,
                        bg="#ffffff",
                        relief=tk.GROOVE,
                        bd=1,
                    )
                    item_frame.pack(
                        fill=tk.X,
                        padx=8,
                        pady=8,
                    )

                    tk.Label(
                        item_frame,
                        text=f"Код {index}",
                        bg="#ffffff",
                        fg="#2c3e50",
                        font=("Arial", 10, "bold"),
                    ).pack(
                        pady=(7, 3),
                    )

                    try:
                        code_image = build_datamatrix_image(code)
                        code_image = code_image.convert("RGB")

                        # Достаточный размер для проверки,
                        # но не слишком большой для списка.
                        code_image = code_image.resize(
                            (220, 220),
                            Image.Resampling.NEAREST,
                        )

                        photo = ImageTk.PhotoImage(code_image)
                        dialog.preview_images.append(photo)

                        image_label = tk.Label(
                            item_frame,
                            image=photo,
                            bg="white",
                        )
                        image_label.pack(
                            pady=4,
                        )

                    except Exception as error:
                        tk.Label(
                            item_frame,
                            text=(
                                "Не удалось сгенерировать "
                                f"изображение:\n{error}"
                            ),
                            bg="#ffffff",
                            fg="#dc3545",
                            justify="center",
                        ).pack(
                            padx=10,
                            pady=10,
                        )

                    code_text = str(code)

                    if len(code_text) > 100:
                        code_text = (
                            code_text[:100]
                            + "..."
                        )

                    tk.Label(
                        item_frame,
                        text=code_text,
                        bg="#ffffff",
                        fg="#6c757d",
                        font=("Consolas", 8),
                        wraplength=530,
                        justify="center",
                    ).pack(
                        padx=10,
                        pady=(3, 8),
                    )

                tk.Label(
                    dialog,
                    text="Что сделать дальше?",
                    bg="#f5f7fa",
                    fg="#2c3e50",
                    font=("Arial", 10, "bold"),
                ).pack(
                    pady=(0, 7),
                )

                buttons = tk.Frame(
                    dialog,
                    bg="#f5f7fa",
                )
                buttons.pack(
                    pady=(0, 14),
                )

                def finish(action):
                    result["action"] = action
                    dialog.destroy()

                tk.Button(
                    buttons,
                    text="🔍 Продолжить поиск",
                    command=lambda: finish("continue"),
                    width=21,
                    bg="#4a9eff",
                    fg="white",
                    activebackground="#3a8eef",
                    activeforeground="white",
                    relief=tk.RAISED,
                    bd=2,
                    font=("Arial", 9, "bold"),
                ).pack(
                    side=tk.LEFT,
                    padx=4,
                )

                tk.Button(
                    buttons,
                    text="✅ Создать PDF",
                    command=lambda: finish("generate"),
                    width=16,
                    bg="#28a745",
                    fg="white",
                    activebackground="#28a745",
                    activeforeground="white",
                    relief=tk.RAISED,
                    bd=2,
                    font=("Arial", 9, "bold"),
                ).pack(
                    side=tk.LEFT,
                    padx=4,
                )

                tk.Button(
                    buttons,
                    text="🖨 Печать",
                    command=lambda: finish("print"),
                    width=12,
                    bg="#4a9eff",
                    fg="white",
                    activebackground="#3a8eef",
                    activeforeground="white",
                    relief=tk.RAISED,
                    bd=2,
                    font=("Arial", 9, "bold"),
                ).pack(
                    side=tk.LEFT,
                    padx=4,
                )

                tk.Button(
                    buttons,
                    text="📊 Excel",
                    command=lambda: finish("excel"),
                    width=11,
                    bg="#4a9eff",
                    fg="white",
                    activebackground="#3a8eef",
                    activeforeground="white",
                    relief=tk.RAISED,
                    bd=2,
                    font=("Arial", 9, "bold"),
                ).pack(
                    side=tk.LEFT,
                    padx=4,
                )

                tk.Button(
                    buttons,
                    text="⏹ Стоп",
                    command=lambda: finish("stop"),
                    width=10,
                    bg="#dc3545",
                    fg="white",
                    activebackground="#dc3545",
                    activeforeground="white",
                    relief=tk.RAISED,
                    bd=2,
                    font=("Arial", 9, "bold"),
                ).pack(
                    side=tk.LEFT,
                    padx=4,
                )

                dialog.protocol(
                    "WM_DELETE_WINDOW",
                    lambda: finish("stop"),
                )

                def on_destroy(event):
                    if event.widget is dialog:
                        try:
                            preview_canvas.unbind_all(
                                "<MouseWheel>"
                            )
                            preview_canvas.unbind_all(
                                "<Button-4>"
                            )
                            preview_canvas.unbind_all(
                                "<Button-5>"
                            )
                        except tk.TclError:
                            pass

                        dialog_event.set()

                dialog.bind(
                    "<Destroy>",
                    on_destroy,
                )

            except Exception as error:
                log(f"preview window error: {error}")

                messagebox.showerror(
                    "Ошибка предпросмотра",
                    f"Не удалось создать окно предпросмотра:\n{error}",
                    parent=self.root,
                )

                dialog_event.set()

        self.ui_callback(show_dialog)
        dialog_event.wait()

        return result["action"]

    def _format_seconds(self, seconds):
        """Форматирует секунды в строку."""
        from logger import format_seconds

        return format_seconds(seconds)