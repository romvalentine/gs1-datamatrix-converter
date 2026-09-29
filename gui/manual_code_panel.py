from logger import log
import tkinter as tk
from tkinter import messagebox
import re


class ManualCodePanel(tk.LabelFrame):
    def __init__(
        self,
        parent,
        on_generate,
    ):
        super().__init__(
            parent,
            text="✏️ Ручной ввод кодов",
            padx=10,
            pady=10,
            bg="#ffffff",
            fg="#2c3e50",
        )

        self.on_generate = on_generate
        self.action_var = tk.StringVar(value="open")
        self.placeholder_text = (
            "Пример:\n"
            "0104607066411670215Ur(dxX:vVPNw<GS>91EE12<GS>92P6K7dOfl2pYk66zqbsYPEZKdT4TmMZZjwZXBMmvoqgg=\n"
            "0104670064651690215bQ\"kQ<GS>93z58v"
        )

        self.buttons = {}

        self.build_interface()

        self.text_widget.bind_class(
            "Text",
            "<Control-Key>",
            lambda e: None,
        )

        # Показываем placeholder при старте
        self._show_placeholder()

    def build_interface(self):
        self.columnconfigure(0, weight=1)

        input_frame = tk.Frame(
            self,
            bg="#ffffff",
        )
        input_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 6),
        )
        input_frame.columnconfigure(0, weight=1)

        self.text_widget = tk.Text(
            input_frame,
            height=4,
            wrap=tk.NONE,
            fg="gray",
            bg="#f5f7fa",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#e1e5eb",
            highlightcolor="#4a9eff",
        )
        self.text_widget.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        self.clear_button = tk.Button(
            input_frame,
            text="✕",
            command=self.clear,
            width=3,
            fg="white",
            bg="#dc3545",
            activebackground="#dc3545",
            activeforeground="white",
            relief=tk.RAISED,
            bd=1,
            cursor="hand2",
        )
        self.clear_button.grid(
            row=0,
            column=1,
            sticky="n",
            padx=(5, 0),
        )

        self.text_widget.bind(
            "<FocusIn>",
            self._on_focus_in,
        )
        self.text_widget.bind(
            "<FocusOut>",
            self._on_focus_out,
        )

        self.create_context_menu()

        # Все кнопки находятся в одной компактной строке.
        controls_frame = tk.Frame(
            self,
            bg="#ffffff",
        )
        controls_frame.grid(
            row=1,
            column=0,
            sticky="w",
        )

        self.buttons = {}

        actions = [
            ("📂 Открыть", "open"),
            ("🖨 Печать", "print"),
        ]

        for index, (text, value) in enumerate(actions):
            button = tk.Button(
                controls_frame,
                text=text,
                command=lambda value=value: self.set_action(value),
                bg="#f0f0f0",
                fg="#2c3e50",
                activebackground="#4a9eff",
                activeforeground="white",
                relief=tk.RAISED,
                bd=2,
                width=12,
                font=("Arial", 9),
            )
            button.grid(
                row=0,
                column=index,
                padx=(0, 5),
            )
            self.buttons[value] = button

        self.generate_button = tk.Button(
            controls_frame,
            text="▶ Сгенерировать",
            command=self.handle_generate,
            bg="#28a745",
            fg="white",
            activebackground="#28a745",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            font=("Arial", 10, "bold"),
        )
        self.generate_button.grid(
            row=0,
            column=2,
            padx=(8, 0),
        )

        self.update_buttons()

    def set_action(self, action):
        self.action_var.set(action)
        self.update_buttons()

    def update_buttons(self):
        current = self.action_var.get()

        for value, button in self.buttons.items():
            if value == current:
                button.config(
                    bg="#4a9eff",
                    fg="white",
                    relief=tk.SUNKEN,
                )
            else:
                button.config(
                    bg="#f0f0f0",
                    fg="#2c3e50",
                    relief=tk.RAISED,
                )

    def _show_placeholder(self):
        """Показать подсказку в поле"""
        current = self.text_widget.get("1.0", tk.END).strip()
        if not current:
            self.text_widget.config(fg="gray")
            self.text_widget.insert("1.0", self.placeholder_text)

    def _hide_placeholder(self):
        """Скрыть подсказку"""
        current = self.text_widget.get("1.0", tk.END).strip()
        if current == self.placeholder_text:
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.config(fg="#2c3e50")

    def _on_focus_in(self, event):
        self._hide_placeholder()

    def _on_focus_out(self, event):
        if not self.text_widget.get("1.0", tk.END).strip():
            self._show_placeholder()

    def create_context_menu(self):
        self.context_menu = tk.Menu(
            self.text_widget,
            tearoff=0,
        )

        self.context_menu.add_command(
            label="📋 Вставить",
            command=lambda: self.text_widget.event_generate("<<Paste>>"),
        )

        self.context_menu.add_command(
            label="📄 Копировать",
            command=lambda: self.text_widget.event_generate("<<Copy>>"),
        )

        self.context_menu.add_command(
            label="✂️ Вырезать",
            command=lambda: self.text_widget.event_generate("<<Cut>>"),
        )

        self.context_menu.add_separator()

        self.context_menu.add_command(
            label="🗑 Очистить поле",
            command=self.clear,
        )

        self.text_widget.bind(
            "<Button-3>",
            self.show_context_menu,
        )

    def show_context_menu(self, event):
        self.text_widget.focus_set()
        self.context_menu.tk_popup(
            event.x_root,
            event.y_root,
        )

    def handle_generate(self):
        # Скрываем placeholder перед генерацией
        self._hide_placeholder()

        codes = self.get_codes()

        if not codes:
            messagebox.showwarning(
                "Ручной ввод",
                "Введите хотя бы один код.",
                parent=self,
            )
            return

        if self.on_generate:
            self.on_generate(
                codes,
                self.action_var.get(),
            )

    def normalize_code(self, code: str) -> str:
        """
        Нормализует код GS1 DataMatrix:

        Полный формат: FNC1 + 01 + GTIN(14) + 21 + Serial(6 или 13) + GS + 91 + Key(4) + GS + 92 + Crypto(44)
        Укороченный формат: FNC1 + 01 + GTIN(14) + 21 + Serial(6 или 13) + GS + 93 + Crypto(4)
        """
        # Заменяем разделители групп на \x1d
        code = (
            code.replace("{GS}", "\x1d")
                .replace("<GS>", "\x1d")
        )

        # Если код не содержит \x1d — добавляем структуру
        if "\x1d" not in code and code.startswith("01"):
            # Определяем формат по позиции 93 или 91/92
            # 93: перед последними 4 символами (93 + 4)
            # 92: перед последними 44 символами (92 + 44)
            # 91: перед 92 + 44 + 2 = перед позицией 92

            if len(code) >= 6 and code[-6:-4] == "93":
                # Укороченный формат: ... + 93 + Crypto(4)
                pos_93 = len(code) - 6
                code = code[:pos_93] + "\x1d" + code[pos_93:]
            elif len(code) >= 46 and code[-46:-44] == "92":
                # Полный формат: ... + 91 + Key(4) + 92 + Crypto(44)
                pos_92 = len(code) - 46
                pos_91 = pos_92 - 6  # 92(2) + Key(4) = 6 символов до 91

                # Добавляем \x1d перед 91
                if code[pos_91:pos_91+2] == "91":
                    code = code[:pos_91] + "\x1d" + code[pos_91:]
                    pos_92 += 1  # Сдвиг на 1

                # Добавляем \x1d перед 92
                code = code[:pos_92] + "\x1d" + code[pos_92:]

        # Добавляем FNC1 в начало, только если его ещё нет.
        if not code.startswith("\x1d"):
            code = "\x1d" + code

        # Убираем возможные дублирующие \x1d в начале.
        # Например, превращаем "\x1d\x1d01..." в "\x1d01..."
        while code.startswith("\x1d\x1d"):
            code = code[1:]

        return code

    def get_codes(self):
        raw = self.text_widget.get("1.0", tk.END)

        # Убираем placeholder, если он есть
        if raw.strip() == self.placeholder_text:
            return []

        log(
            f"manual_code_panel get_codes raw: {raw!r}"
        )

        # Разбиваем только по реальным концам строк
        lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        codes = []

        for line in lines:
            value = line.strip()

            if value:
                # Нормализуем код
                normalized = self.normalize_code(value)
                codes.append(normalized)

        log(
            f"manual_code_panel get_codes RETURN: {codes!r}"
        )

        return codes

    def clear(self):
        if (
            self.text_widget.cget("state") == tk.DISABLED
        ):
            return

        self.text_widget.delete("1.0", tk.END)
        self._show_placeholder()

    def set_enabled(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED

        self.text_widget.config(state=state)
        self.generate_button.config(state=state)
        self.clear_button.config(state=state)