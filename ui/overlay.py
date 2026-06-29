import tkinter as tk
import ctypes
import ctypes.wintypes
import threading

# Константи Windows API для click-through вікна
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

# Кольори
COLOR_BG = "#1a1a1a"
COLOR_TEXT = "#e0e0e0"
COLOR_BEST = "#FFD700"       # золотий для найдорожчого
COLOR_PRICE = "#aaffaa"      # зелений для ціни
COLOR_TITLE = "#888888"
COLOR_BORDER = "#444444"


class GemOverlay:
    def __init__(self):
        self._root = None
        self._thread = None
        self._visible = False
        self._pending_results = None
        self._lock = threading.Lock()

    def start(self):
        """Запускає overlay у окремому потоці."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        self._root = tk.Tk()
        self._root.title("PoE Gem Overlay")
        self._root.overrideredirect(True)          # без рамки та заголовку
        self._root.attributes("-topmost", True)    # завжди поверх
        self._root.attributes("-alpha", 0.92)
        self._root.configure(bg=COLOR_BG)
        self._root.geometry("320x50+20+100")

        # Зробити вікно click-through через Windows API
        self._make_click_through()

        # Головний фрейм
        self._frame = tk.Frame(self._root, bg=COLOR_BG, padx=8, pady=6)
        self._frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        self._title_label = tk.Label(
            self._frame,
            text="PoE Gem Prices",
            font=("Consolas", 9),
            fg=COLOR_TITLE,
            bg=COLOR_BG,
            anchor="w",
        )
        self._title_label.pack(fill=tk.X)

        # Контейнер для рядків каменів
        self._gems_frame = tk.Frame(self._frame, bg=COLOR_BG)
        self._gems_frame.pack(fill=tk.BOTH, expand=True)

        # Перевіряємо чи є очікувані оновлення кожні 100 мс
        self._root.after(100, self._check_updates)
        self._root.mainloop()

    def _make_click_through(self):
        """Дозволяє клікати крізь вікно overlay."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self._root.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            )
        except Exception as e:
            print(f"[overlay] Click-through не вдалося: {e}")

    def _check_updates(self):
        """Перевіряє і застосовує оновлення UI (викликається з потоку tkinter)."""
        with self._lock:
            results = self._pending_results
            self._pending_results = None

        if results is not None:
            self._render(results)

        if self._root:
            self._root.after(100, self._check_updates)

    def _render(self, results: list):
        """Перемальовує список каменів."""
        # Очищаємо старі рядки
        for widget in self._gems_frame.winfo_children():
            widget.destroy()

        if not results:
            self._root.geometry("320x30+20+100")
            return

        # Малюємо рядок для кожного каменя
        for gem in results:
            row = tk.Frame(self._gems_frame, bg=COLOR_BG)
            row.pack(fill=tk.X, pady=1)

            color = COLOR_BEST if gem["is_best"] else COLOR_TEXT
            prefix = "★ " if gem["is_best"] else "  "

            name_label = tk.Label(
                row,
                text=f"{prefix}{gem['name']}",
                font=("Consolas", 10, "bold" if gem["is_best"] else "normal"),
                fg=color,
                bg=COLOR_BG,
                anchor="w",
            )
            name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

            price_text = f"{gem['divine']:.2f}d" if gem["divine"] >= 0.01 else f"{gem['chaos']:.0f}c"
            price_label = tk.Label(
                row,
                text=price_text,
                font=("Consolas", 10, "bold"),
                fg=COLOR_BEST if gem["is_best"] else COLOR_PRICE,
                bg=COLOR_BG,
                anchor="e",
                width=8,
            )
            price_label.pack(side=tk.RIGHT)

        # Підлаштовуємо висоту вікна
        height = 30 + len(results) * 22
        self._root.geometry(f"320x{height}+20+100")

    def update(self, results: list):
        """Потокобезпечне оновлення overlay."""
        with self._lock:
            self._pending_results = results

    def clear(self):
        """Очищає overlay."""
        self.update([])

    def show(self):
        """Показує overlay."""
        if self._root:
            self._root.after(0, lambda: self._root.deiconify())

    def hide(self):
        """Ховає overlay."""
        if self._root:
            self._root.after(0, lambda: self._root.withdraw())

    def toggle(self):
        """Перемикає видимість."""
        if self._visible:
            self.hide()
            self._visible = False
        else:
            self.show()
            self._visible = True


# --- Тест ---
if __name__ == "__main__":
    import time

    overlay = GemOverlay()
    overlay.start()
    time.sleep(0.5)  # чекаємо запуску tkinter

    # Показуємо тестові дані
    test_results = [
        {"name": "Fireball of Combusting", "divine": 1.25, "chaos": 250.0, "is_best": True},
        {"name": "Spark of Noxious Propagation", "divine": 0.45, "chaos": 90.0, "is_best": False},
        {"name": "Flameblast of Contraction", "divine": 0.12, "chaos": 24.0, "is_best": False},
    ]

    print("Показую тестовий overlay (5 секунд)...")
    overlay.update(test_results)
    time.sleep(5)

    print("Очищую...")
    overlay.clear()
    time.sleep(2)
    print("Готово")
