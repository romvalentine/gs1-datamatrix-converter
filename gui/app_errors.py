import tkinter as tk

from tkinter import messagebox, ttk
from pathlib import Path

from logger import log


class ErrorHandlingMixin:
    """Миксин для обработки ошибок."""
    
    def handle_generation_result(self, result, output_path):
        from services.pdf_service import is_complete, get_output_path
        
        if is_complete(result):
            pdf_path = get_output_path(result)
            if pdf_path is not None:
                codes = result.get('successful_codes', [])
                self.apply_after_action(pdf_path, codes)
            return

        log("PDF неполный: автоматические открытие и печать запрещены")
        current_mode = self.ui.mode_panel.get_mode()

        self.ui_callback(
            lambda: self.handle_incomplete_result(
                result,
                output_path,
                current_mode,
            )
        )

    def handle_incomplete_result(
        self,
        result,
        output_path,
        current_mode,
    ):
        from services.pdf_service import create_recognized_pdf, is_complete, get_output_path
        from core.pdf_to_excel import extract_codes_from_pdf
        
        # Сначала экспортируем в Excel если выбрано
        if self.after_action == "excel":
            excel_path = output_path.with_suffix('.xlsx')
            codes = result.get('successful_codes', [])
            extract_codes_from_pdf(str(output_path), codes, str(excel_path))
            self.ui.set_status(
                f"📊 Коды экспортированы в Excel: {excel_path}",
                "green",
            )
        
        from gui.incomplete_dialog import show_incomplete_dialog
        action = show_incomplete_dialog(
            parent=self.root,
            result=result,
            current_mode=current_mode,
        )

        if action == "cancel":
            self.ui.set_status(
                "Печать и открытие отменены",
                "darkorange",
            )
            return

        if action == "retry_errors":
            # Повторная обработка только ошибочных листов
            errors = result.get('errors', [])
            error_pages = []
            for error in errors:
                if error.startswith('Лист '):
                    try:
                        page_num = int(error.split(':')[0].replace('Лист ', '').strip())
                        error_pages.append(page_num)
                    except:
                        pass
            
            self.retry_error_pages(output_path, error_pages, current_mode)
            return

        if action == "print_recognized":
            recognized_result = create_recognized_pdf(
                generation_result=result,
                output_path=output_path,
            )

            if not is_complete(recognized_result):
                messagebox.showwarning(
                    "Нет кодов",
                    "Нет полностью распознанных кодов для печати.",
                )
                return

            recognized_path = get_output_path(recognized_result)
            if recognized_path is None:
                return

            try:
                from services.printing_service import print_pdf
                print_pdf(
                    recognized_path,
                    self.selected_printer,
                    self.print_settings,
                )
                self.ui.set_status(
                    "Напечатаны только распознанные коды",
                    "green",
                )
            except Exception as error:
                log(f"recognized print error: {error}")
                messagebox.showerror("Ошибка печати", str(error))
            return

        if action.startswith("mode:"):
            new_mode = action.split(":", 1)[1]
            self.repeat_conversion(new_mode)

    def retry_error_pages(self, result_pdf_path, error_pages, current_mode):
        """
        Повторная обработка только ошибочных листов.
        """
        if not error_pages:
            messagebox.showinfo(
                "Нет ошибок",
                "Нет листов с ошибками для повторной обработки.",
            )
            return
        
        # Создаём диалог с выпадающим списком
        dialog = tk.Toplevel(self.root)
        dialog.title("Режим обработки")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(
            dialog,
            text=f"Обработать {len(error_pages)} листов с ошибками:",
            font=("Arial", 10, "bold"),
        ).pack(pady=10)
        
        tk.Label(
            dialog,
            text=f"Листы: {error_pages}",
            fg="darkorange",
        ).pack(pady=5)
        
        tk.Label(
            dialog,
            text="Выберите режим:",
        ).pack(pady=5)
        
        mode_var = tk.StringVar(value="safe")
        
        mode_box = ttk.Combobox(
            dialog,
            textvariable=mode_var,
            values=["safe", "photo", "manual"],
            state="readonly",
            width=20,
        )
        mode_box.pack(pady=5)
        
        selected_mode = {"value": None}
        
        def on_ok():
            selected_mode["value"] = mode_var.get()
            dialog.destroy()
        
        def on_cancel():
            selected_mode["value"] = None
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(
            btn_frame,
            text="OK",
            command=on_ok,
            width=10,
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="Отмена",
            command=on_cancel,
            width=10,
        ).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()
        
        mode = selected_mode["value"]
        
        if not mode:
            return
        
        self.ui.set_status(
            f"Повторная обработка листов {error_pages} в режиме {mode}...",
            "darkorange",
        )
        
        # Сохраняем error_pages ПЕРЕД вызовом process_error_pages_only
        self.forced_mode = mode
        self.error_pages = error_pages
        
        # Вызываем напрямую, НЕ через root.after
        self.process_error_pages_only(result_pdf_path, error_pages, mode)
    
    def process_error_pages_only(self, result_pdf_path, error_pages, mode):
        """
        Открывает ОРИГИНАЛЬНЫЙ PDF и обрабатывает только ошибочные листы.
        """
        log(f"=== process_error_pages_only START ===")
        log(f"result_pdf_path: {result_pdf_path}")
        log(f"error_pages: {error_pages}")
        log(f"mode: {mode}")
        
        # Используем оригинальный файл, а не результат
        original_pdf_path = getattr(self, 'original_file_path', None)
        
        log(f"original_file_path: {original_pdf_path}")
        
        if not original_pdf_path or not original_pdf_path.exists():
            messagebox.showerror(
                "Ошибка",
                "Оригинальный файл не найден.\n"
                "Запустите обработку заново.",
            )
            return
        
        # Загружаем существующие коды из Excel
        import pandas as pd
        excel_path = result_pdf_path.with_suffix('.xlsx')
        
        try:
            df = pd.read_excel(excel_path)
            existing_codes = df['code'].tolist() if 'code' in df.columns else []
        except Exception as e:
            log(f"Не удалось загрузить Excel: {e}")
            existing_codes = []
        
        # Обрабатываем только ошибочные листы из ОРИГИНАЛЬНОГО файла
        new_codes = []
        success_count = 0
        
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(original_pdf_path)
            
            self.ui.set_status(
                f"Обработка {len(error_pages)} листов с ошибками из {original_pdf_path.name}...",
                "darkorange",
            )
            
            for idx, page_num in enumerate(error_pages, start=1):
                if page_num < 1 or page_num > len(doc):
                    new_codes.append(None)
                    continue
                
                page = doc[page_num - 1]
                
                # Рендерим страницу
                mat = fitz.Matrix(150/72, 150/72)
                pix = page.get_pixmap(matrix=mat)
                
                import cv2
                import numpy as np
                from io import BytesIO
                from PIL import Image
                
                # Конвертируем в формат для scanner
                img_data = pix.tobytes("png")
                img = Image.open(BytesIO(img_data))
                
                # Используем scanner.scan_image
                try:
                    codes = self.scanner.scan_image(img, mode=mode)
                    code = codes[0] if codes and len(codes) > 0 else None
                except Exception as e:
                    log(f"scan_image error on page {page_num}: {e}")
                    code = None
                
                if code:
                    new_codes.append(code)
                    success_count += 1
                    self.ui.set_status(
                        f"✅ Лист {page_num}: код распознан! ({success_count}/{len(error_pages)})",
                        "green",
                    )
                else:
                    new_codes.append(None)
                    self.ui.set_status(
                        f"❌ Лист {page_num}: код не распознан ({success_count}/{len(error_pages)})",
                        "red",
                    )
            
            doc.close()
            
        except Exception as e:
            messagebox.showerror("Ошибка обработки", str(e))
            import traceback
            log(f"process_error_pages error: {traceback.format_exc()}")
            return
        
        # Обновляем коды: заменяем None на новые коды
        all_codes = existing_codes.copy()
        
        # Находим индексы ошибочных листов и обновляем коды
        for i, page_num in enumerate(error_pages):
            if i < len(new_codes) and new_codes[i]:
                # Находим индекс кода для этого листа
                code_index = page_num - 1
                if code_index < len(all_codes):
                    all_codes[code_index] = new_codes[i]
        
        # Пересоздаём PDF со всеми кодами
        from services.pdf_service import create_pdf
        output_path = result_pdf_path.parent / (result_pdf_path.stem + " (обновлено).pdf")
        
        generation_result = create_pdf(
            codes=all_codes,
            output_path=output_path,
        )
        
        # Обновляем Excel
        from core.pdf_to_excel import extract_codes_from_pdf
        excel_path = output_path.with_suffix('.xlsx')
        extract_codes_from_pdf(str(output_path), all_codes, str(excel_path))
        
        self.ui.set_status(
            f"✅ Обработано {len(error_pages)} листов. Распознано: {success_count}",
            "green",
        )
        
        messagebox.showinfo(
            "Готово",
            f"Обработано {len(error_pages)} листов.\n"
            f"✅ Распознано кодов: {success_count}\n"
            f"❌ Не распознано: {len(error_pages) - success_count}\n\n"
            f"Файлы обновлены:\n{output_path}",
        )
        
        # Очищаем error_pages
        self.error_pages = None
        self.forced_mode = None

    def repeat_conversion(self, new_mode):
        self.forced_mode = new_mode
        self.ui.set_status(
            f"Повторная проверка в режиме {new_mode}",
            "darkorange",
        )
        self.root.after(300, self.start_conversion)