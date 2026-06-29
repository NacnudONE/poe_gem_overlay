import tkinter as tk
from tkinter import ttk
import threading
import time
import queue
import config
from core import trade_fetcher
from capture import tooltip_scanner
from ui.overlay import GemOverlay

# --- Кольори GUI ---
BG = "#1e1e2e"
BG2 = "#2a2a3e"
ACCENT = "#c9a96e"       # золотий PoE
GREEN = "#50fa7b"
RED = "#ff5555"
GRAY = "#888888"
TEXT = "#cdd6f4"
TEXT2 = "#a6adc8"

SCAN_INTERVAL = 0.5


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("PoE Gem Overlay")
        self.geometry("420x520")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.attributes("-topmost", False)

        # Внутрішній стан
        self._running = False
        self._scan_thread = None
        self._overlay = GemOverlay()
        self._log_queue = queue.Queue()
        self._seen_gems = {}   # накопичуємо до 3 каменів поки вікно відкрите

        self._build_ui()
        self._overlay.start()
        self.after(200, self._load_prices)
        self.after(100, self._process_log)
        self.after(300, self._fetch_leagues_async)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # Заголовок
        hdr = tk.Frame(self, bg=BG, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="⚗  PoE Gem Overlay", font=("Consolas", 16, "bold"),
                 fg=ACCENT, bg=BG).pack()
        tk.Label(hdr, text="Path of Exile 1 · Transfigured Gems", font=("Consolas", 9),
                 fg=TEXT2, bg=BG).pack()

        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=10)

        # --- Блок налаштувань ---
        cfg_frame = tk.LabelFrame(self, text=" Налаштування ", font=("Consolas", 9),
                                   fg=TEXT2, bg=BG, bd=1, relief="groove", padx=10, pady=8)
        cfg_frame.pack(fill=tk.X, padx=14, pady=(10, 6))

        # Ліга
        row1 = tk.Frame(cfg_frame, bg=BG)
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="Ліга:", width=12, anchor="w",
                 font=("Consolas", 10), fg=TEXT, bg=BG).pack(side=tk.LEFT)
        self._league_var = tk.StringVar(value=config.LEAGUE)
        self._league_combo = ttk.Combobox(
            row1,
            textvariable=self._league_var,
            values=trade_fetcher._DEFAULT_LEAGUES,
            font=("Consolas", 10),
            width=20,
            state="readonly",
        )
        self._league_combo.pack(side=tk.LEFT)

        # Гаряча клавіша
        row2 = tk.Frame(cfg_frame, bg=BG)
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="Клавіша вкл/вкл:", width=16, anchor="w",
                 font=("Consolas", 10), fg=TEXT, bg=BG).pack(side=tk.LEFT)
        tk.Label(row2, text=config.HOTKEY, font=("Consolas", 10, "bold"),
                 fg=ACCENT, bg=BG).pack(side=tk.LEFT)

        # --- Блок статусу ---
        st_frame = tk.LabelFrame(self, text=" Статус ", font=("Consolas", 9),
                                  fg=TEXT2, bg=BG, bd=1, relief="groove", padx=10, pady=8)
        st_frame.pack(fill=tk.X, padx=14, pady=6)

        row_prices = tk.Frame(st_frame, bg=BG)
        row_prices.pack(fill=tk.X, pady=2)
        tk.Label(row_prices, text="Ціни:", width=12, anchor="w",
                 font=("Consolas", 10), fg=TEXT, bg=BG).pack(side=tk.LEFT)
        self._prices_label = tk.Label(row_prices, text="Завантаження...",
                                      font=("Consolas", 10), fg=GRAY, bg=BG, anchor="w")
        self._prices_label.pack(side=tk.LEFT)


        row_scan = tk.Frame(st_frame, bg=BG)
        row_scan.pack(fill=tk.X, pady=2)
        tk.Label(row_scan, text="Сканування:", width=12, anchor="w",
                 font=("Consolas", 10), fg=TEXT, bg=BG).pack(side=tk.LEFT)
        self._scan_label = tk.Label(row_scan, text="Зупинено",
                                    font=("Consolas", 10), fg=RED, bg=BG, anchor="w")
        self._scan_label.pack(side=tk.LEFT)

        # --- Кнопки ---
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill=tk.X, padx=14, pady=8)

        self._start_btn = tk.Button(
            btn_frame, text="▶  Старт",
            font=("Consolas", 10, "bold"), bg=ACCENT, fg="#1e1e2e",
            activebackground="#e8c27e", activeforeground="#1e1e2e",
            relief="flat", bd=0, padx=12, pady=8, cursor="hand2",
            command=self._toggle_scan, state=tk.DISABLED
        )
        self._start_btn.pack(fill=tk.X)

        btn_row2 = tk.Frame(self, bg=BG)
        btn_row2.pack(fill=tk.X, padx=14, pady=(0, 6))
        tk.Button(
            btn_row2, text="🔄  Оновити ціни",
            font=("Consolas", 9), bg=BG2, fg=TEXT2,
            activebackground="#3a3a5e", activeforeground=TEXT,
            relief="flat", bd=0, padx=8, pady=5, cursor="hand2",
            command=self._reload_prices
        ).pack(side=tk.RIGHT)
        tk.Button(
            btn_row2, text="🗑  Очистити",
            font=("Consolas", 9), bg=BG2, fg=TEXT2,
            activebackground="#3a3a5e", activeforeground=TEXT,
            relief="flat", bd=0, padx=8, pady=5, cursor="hand2",
            command=self._clear_gems
        ).pack(side=tk.RIGHT, padx=(0, 6))

        # --- Лог ---
        log_frame = tk.LabelFrame(self, text=" Лог ", font=("Consolas", 9),
                                   fg=TEXT2, bg=BG, bd=1, relief="groove")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))

        self._log = tk.Text(log_frame, font=("Consolas", 9), bg=BG2, fg=TEXT2,
                            relief="flat", bd=4, state=tk.DISABLED,
                            wrap=tk.WORD, height=8)
        self._log.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(log_frame, command=self._log.yview)
        self._log["yscrollcommand"] = scroll.set

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ Логіка

    def _log_msg(self, msg: str):
        self._log_queue.put(msg)

    def _process_log(self):
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self._log.configure(state=tk.NORMAL)
                self._log.insert(tk.END, msg + "\n")
                self._log.see(tk.END)
                self._log.configure(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.after(150, self._process_log)

    def _load_prices(self):
        league = self._league_var.get().strip()
        config.LEAGUE = league
        trade_fetcher.LEAGUE = league
        self._prices_label.config(text="Готово  ✓", fg=GREEN)
        self._log_msg(f"Ліга: {league}. Ціни з PoE Trade API (level 1)")
        self._check_ready()

    def _reload_prices(self):
        self._load_prices()

    def _fetch_leagues_async(self):
        threading.Thread(target=self._do_fetch_leagues, daemon=True).start()

    def _do_fetch_leagues(self):
        leagues = trade_fetcher.fetch_leagues()
        self.after(0, lambda: self._league_combo.configure(values=leagues))

    def _clear_gems(self):
        self._seen_gems = {}
        self._overlay.clear()
        self._log_msg("Список каменів очищено")

    def _check_ready(self):
        self._start_btn.config(state=tk.NORMAL)

    def _toggle_scan(self):
        if self._running:
            self._stop_scan()
        else:
            self._start_scan()

    def _start_scan(self):
        self._running = True
        self._seen_gems = {}
        self._start_btn.config(text="⏹  Стоп", bg=RED, fg="white",
                               activebackground="#cc3333")
        self._scan_label.config(text="Активне  ●", fg=GREEN)
        self._log_msg("Сканування запущено — наводь мишу на камені!")
        self._scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._scan_thread.start()

    def _stop_scan(self):
        self._running = False
        self._overlay.clear()
        self._start_btn.config(text="▶  Старт", bg=ACCENT, fg="#1e1e2e",
                               activebackground="#e8c27e")
        self._scan_label.config(text="Зупинено", fg=RED)
        self._log_msg("Сканування зупинено")

    def _build_overlay_results(self) -> list:
        items = list(self._seen_gems.values())
        if not items:
            return []
        best_idx = max(range(len(items)), key=lambda i: items[i]["divine"])
        for i, item in enumerate(items):
            item["is_best"] = (i == best_idx)
        items.sort(key=lambda x: x["divine"], reverse=True)
        return items

    def _scan_loop(self):
        last_ocr_name = None
        divine_rate = trade_fetcher._fetch_divine_rate(config.LEAGUE)

        while self._running:
            try:
                gem_name = tooltip_scanner.scan_tooltip()

                if gem_name and gem_name != last_ocr_name:
                    last_ocr_name = gem_name
                    # Ціну шукаємо в окремому потоці щоб не блокувати сканування
                    threading.Thread(
                        target=self._fetch_and_add_gem,
                        args=(gem_name, divine_rate),
                        daemon=True
                    ).start()

            except Exception as e:
                self._log_msg(f"Помилка: {e}")

            time.sleep(SCAN_INTERVAL)

    def _fetch_and_add_gem(self, gem_name: str, divine_rate: float):
        self._log_msg(f"Шукаю ціну: {gem_name}...")
        gem_data = trade_fetcher.fetch_gem_price(gem_name, config.LEAGUE)
        if gem_data:
            self._seen_gems[gem_data["name"]] = {
                "name": gem_data["name"],
                "divine": gem_data["divine"],
                "chaos": gem_data["chaos"],
                "is_best": False,
            }
            results = self._build_overlay_results()
            self._overlay.update(results)
            listings = gem_data.get("listings", 0)
            self._log_msg(
                f"  {gem_data['name']} — {gem_data['chaos']:.0f}c"
                f" / {gem_data['divine']:.2f}d  ({listings} listings)"
            )
        else:
            self._log_msg(f"  Не знайдено: {gem_name}")

    def _on_close(self):
        self._running = False
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
