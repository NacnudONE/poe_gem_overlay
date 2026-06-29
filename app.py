import tkinter as tk
from tkinter import ttk
import threading
import time
import queue
import webbrowser
import requests
import config
from core import trade_fetcher
from capture import tooltip_scanner
from ui.overlay import GemOverlay
from ui import i18n

# --- Кольори GUI ---
BG = "#1e1e2e"
BG2 = "#2a2a3e"
ACCENT = "#c9a96e"
GREEN = "#50fa7b"
RED = "#ff5555"
GRAY = "#888888"
TEXT = "#cdd6f4"
TEXT2 = "#a6adc8"

SCAN_INTERVAL = 0.5
_RELEASES_URL = "https://github.com/NacnudONE/poe_gem_overlay/releases/latest"


def _is_newer_version(latest: str, current: str) -> bool:
    def parse(v: str):
        try:
            return tuple(int(x) for x in v.strip().split("."))
        except Exception:
            return (0,)
    return parse(latest) > parse(current)


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("PoE Gem Overlay")
        self.geometry("420x520")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.attributes("-topmost", False)

        self._running = False
        self._scan_thread = None
        self._overlay = GemOverlay()
        self._log_queue = queue.Queue()
        self._seen_gems = {}
        self._overlay_drag = False

        self._build_ui()
        self._overlay.start()
        self.after(200, self._load_prices)
        self.after(100, self._process_log)
        self.after(300, self._fetch_leagues_async)
        self.after(2000, self._check_update_async)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # Заголовок
        hdr = tk.Frame(self, bg=BG, pady=12)
        hdr.pack(fill=tk.X)

        tk.Label(hdr, text="⚗  PoE Gem Overlay", font=("Consolas", 16, "bold"),
                 fg=ACCENT, bg=BG).pack()
        tk.Label(hdr, text="Path of Exile 1 · Transfigured Gems", font=("Consolas", 9),
                 fg=TEXT2, bg=BG).pack()

        # Кнопка мови — правий верхній кут
        self._lang_btn = tk.Button(
            hdr, text="🇬🇧 EN",
            font=("Consolas", 8), bg=BG2, fg=TEXT2,
            activebackground="#3a3a5e", activeforeground=TEXT,
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2",
            command=self._toggle_lang,
        )
        self._lang_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=6)

        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=10)

        # --- Банер оновлення (прихований за замовчуванням) ---
        self._update_bar = tk.Frame(self, bg="#1a2800", padx=12, pady=5)
        self._update_lbl = tk.Label(
            self._update_bar, text="",
            font=("Consolas", 9), fg="#aeff55", bg="#1a2800", anchor="w",
        )
        self._update_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._update_btn = tk.Button(
            self._update_bar, text=i18n.t("download_update"),
            font=("Consolas", 9, "bold"), bg="#3a5500", fg="#aeff55",
            activebackground="#4a6a00", activeforeground="#ffffff",
            relief="flat", bd=0, padx=10, pady=2, cursor="hand2",
            command=self._open_update,
        )
        self._update_btn.pack(side=tk.RIGHT)
        # _update_bar не пакуємо — з'явиться тільки при оновленні

        # --- Налаштування ---
        self._cfg_frame = tk.LabelFrame(
            self, text=i18n.t("settings"), font=("Consolas", 9),
            fg=TEXT2, bg=BG, bd=1, relief="groove", padx=10, pady=8,
        )
        self._cfg_frame.pack(fill=tk.X, padx=14, pady=(10, 6))

        row1 = tk.Frame(self._cfg_frame, bg=BG)
        row1.pack(fill=tk.X, pady=3)
        self._league_label = tk.Label(row1, text=i18n.t("league"), width=12, anchor="w",
                                      font=("Consolas", 10), fg=TEXT, bg=BG)
        self._league_label.pack(side=tk.LEFT)
        self._league_var = tk.StringVar(value=config.LEAGUE)
        self._league_combo = ttk.Combobox(
            row1, textvariable=self._league_var,
            values=trade_fetcher._DEFAULT_LEAGUES,
            font=("Consolas", 10), width=20, state="readonly",
        )
        self._league_combo.pack(side=tk.LEFT)

        row2 = tk.Frame(self._cfg_frame, bg=BG)
        row2.pack(fill=tk.X, pady=3)
        self._hotkey_label = tk.Label(row2, text=i18n.t("hotkey"), width=12, anchor="w",
                                      font=("Consolas", 10), fg=TEXT, bg=BG)
        self._hotkey_label.pack(side=tk.LEFT)
        tk.Label(row2, text=config.HOTKEY, font=("Consolas", 10, "bold"),
                 fg=ACCENT, bg=BG).pack(side=tk.LEFT)

        # --- Статус ---
        self._st_frame = tk.LabelFrame(
            self, text=i18n.t("status"), font=("Consolas", 9),
            fg=TEXT2, bg=BG, bd=1, relief="groove", padx=10, pady=8,
        )
        self._st_frame.pack(fill=tk.X, padx=14, pady=6)

        row_prices = tk.Frame(self._st_frame, bg=BG)
        row_prices.pack(fill=tk.X, pady=2)
        self._prices_static = tk.Label(row_prices, text=i18n.t("prices"), width=12, anchor="w",
                                       font=("Consolas", 10), fg=TEXT, bg=BG)
        self._prices_static.pack(side=tk.LEFT)
        self._prices_label = tk.Label(row_prices, text=i18n.t("loading"),
                                      font=("Consolas", 10), fg=GRAY, bg=BG, anchor="w")
        self._prices_label.pack(side=tk.LEFT)

        row_scan = tk.Frame(self._st_frame, bg=BG)
        row_scan.pack(fill=tk.X, pady=2)
        self._scan_static = tk.Label(row_scan, text=i18n.t("scanning"), width=12, anchor="w",
                                     font=("Consolas", 10), fg=TEXT, bg=BG)
        self._scan_static.pack(side=tk.LEFT)
        self._scan_label = tk.Label(row_scan, text=i18n.t("stopped"),
                                    font=("Consolas", 10), fg=RED, bg=BG, anchor="w")
        self._scan_label.pack(side=tk.LEFT)

        # --- Кнопки ---
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill=tk.X, padx=14, pady=8)
        self._start_btn = tk.Button(
            btn_frame, text=i18n.t("start"),
            font=("Consolas", 10, "bold"), bg=ACCENT, fg="#1e1e2e",
            activebackground="#e8c27e", activeforeground="#1e1e2e",
            relief="flat", bd=0, padx=12, pady=8, cursor="hand2",
            command=self._toggle_scan, state=tk.DISABLED,
        )
        self._start_btn.pack(fill=tk.X)

        btn_row2 = tk.Frame(self, bg=BG)
        btn_row2.pack(fill=tk.X, padx=14, pady=(0, 6))
        self._refresh_btn = tk.Button(
            btn_row2, text=i18n.t("refresh"),
            font=("Consolas", 9), bg=BG2, fg=TEXT2,
            activebackground="#3a3a5e", activeforeground=TEXT,
            relief="flat", bd=0, padx=8, pady=5, cursor="hand2",
            command=self._reload_prices,
        )
        self._refresh_btn.pack(side=tk.RIGHT)
        self._clear_btn = tk.Button(
            btn_row2, text=i18n.t("clear"),
            font=("Consolas", 9), bg=BG2, fg=TEXT2,
            activebackground="#3a3a5e", activeforeground=TEXT,
            relief="flat", bd=0, padx=8, pady=5, cursor="hand2",
            command=self._clear_gems,
        )
        self._clear_btn.pack(side=tk.RIGHT, padx=(0, 6))

        self._move_btn = tk.Button(
            btn_row2, text=i18n.t("move_overlay"),
            font=("Consolas", 9), bg=BG2, fg=TEXT2,
            activebackground="#3a3a5e", activeforeground=TEXT,
            relief="flat", bd=0, padx=8, pady=5, cursor="hand2",
            command=self._toggle_overlay_drag,
        )
        self._move_btn.pack(side=tk.LEFT)

        # --- Лог ---
        self._log_frame = tk.LabelFrame(
            self, text=i18n.t("log"), font=("Consolas", 9),
            fg=TEXT2, bg=BG, bd=1, relief="groove",
        )
        self._log_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))
        self._log = tk.Text(self._log_frame, font=("Consolas", 9), bg=BG2, fg=TEXT2,
                            relief="flat", bd=4, state=tk.DISABLED, wrap=tk.WORD, height=8)
        self._log.pack(fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(self._log_frame, command=self._log.yview)
        self._log["yscrollcommand"] = scroll.set

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_lang(self):
        """Оновлює всі підписи після зміни мови."""
        self._cfg_frame.configure(text=i18n.t("settings"))
        self._st_frame.configure(text=i18n.t("status"))
        self._log_frame.configure(text=i18n.t("log"))
        self._league_label.configure(text=i18n.t("league"))
        self._hotkey_label.configure(text=i18n.t("hotkey"))
        self._prices_static.configure(text=i18n.t("prices"))
        self._scan_static.configure(text=i18n.t("scanning"))
        self._refresh_btn.configure(text=i18n.t("refresh"))
        self._clear_btn.configure(text=i18n.t("clear"))
        self._move_btn.configure(
            text=i18n.t("lock_overlay") if self._overlay_drag else i18n.t("move_overlay")
        )
        self._update_btn.configure(text=i18n.t("download_update"))
        # Оновлюємо текст банера якщо він видимий
        cur_text = self._update_lbl.cget("text")
        if cur_text:
            # Витягуємо версію з поточного тексту і перекладаємо
            import re
            m = re.search(r"v[\d.]+", cur_text)
            if m:
                self._update_lbl.configure(
                    text=i18n.t("update_available", version=m.group())
                )

        # Кнопка старт/стоп
        if self._running:
            self._start_btn.configure(text=i18n.t("stop"))
            self._scan_label.configure(text=i18n.t("active"))
        else:
            self._start_btn.configure(text=i18n.t("start"))
            self._scan_label.configure(text=i18n.t("stopped"))

    def _toggle_lang(self):
        if i18n.get_lang() == "uk":
            i18n.set_lang("en")
            self._lang_btn.configure(text="🇺🇦 UA")
        else:
            i18n.set_lang("uk")
            self._lang_btn.configure(text="🇬🇧 EN")
        self._apply_lang()

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
        self._prices_label.config(text=i18n.t("ready"), fg=GREEN)
        self._log_msg(i18n.t("league_loaded", league=league))
        self._check_ready()

    def _reload_prices(self):
        self._load_prices()

    def _fetch_leagues_async(self):
        threading.Thread(target=self._do_fetch_leagues, daemon=True).start()

    def _do_fetch_leagues(self):
        leagues = trade_fetcher.fetch_leagues()
        self.after(0, lambda: self._league_combo.configure(values=leagues))

    # ------------------------------------------------------------------ Оновлення

    def _check_update_async(self):
        threading.Thread(target=self._do_check_update, daemon=True).start()

    def _do_check_update(self):
        try:
            r = requests.get(
                "https://api.github.com/repos/NacnudONE/poe_gem_overlay/releases/latest",
                timeout=8,
            )
            if not r.ok:
                return
            tag = r.json().get("tag_name", "").lstrip("v")
            if tag and _is_newer_version(tag, config.VERSION):
                self.after(0, lambda: self._show_update_banner(f"v{tag}"))
        except Exception:
            pass

    def _show_update_banner(self, version: str):
        self._update_lbl.configure(text=i18n.t("update_available", version=version))
        self._update_bar.pack(fill=tk.X, padx=0, pady=0, after=None)
        # Вставляємо одразу після сепаратора (перед _cfg_frame)
        self._update_bar.pack_configure(before=self._cfg_frame)

    def _open_update(self):
        webbrowser.open(_RELEASES_URL)

    def _toggle_overlay_drag(self):
        if not self._overlay_drag:
            self._overlay_drag = True
            self._overlay.unlock()
            self._move_btn.configure(text=i18n.t("lock_overlay"), bg=ACCENT, fg="#1e1e2e")
        else:
            self._overlay_drag = False
            self._overlay.lock()
            self._move_btn.configure(text=i18n.t("move_overlay"), bg=BG2, fg=TEXT2)

    def _clear_gems(self):
        self._seen_gems = {}
        self._overlay.clear()
        self._log_msg(i18n.t("gems_cleared"))

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
        self._start_btn.config(text=i18n.t("stop"), bg=RED, fg="white",
                               activebackground="#cc3333")
        self._scan_label.config(text=i18n.t("active"), fg=GREEN)
        self._log_msg(i18n.t("scan_started"))
        self._scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._scan_thread.start()

    def _stop_scan(self):
        self._running = False
        self._overlay.clear()
        self._start_btn.config(text=i18n.t("start"), bg=ACCENT, fg="#1e1e2e",
                               activebackground="#e8c27e")
        self._scan_label.config(text=i18n.t("stopped"), fg=RED)
        self._log_msg(i18n.t("scan_stopped"))

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
                    threading.Thread(
                        target=self._fetch_and_add_gem,
                        args=(gem_name, divine_rate),
                        daemon=True,
                    ).start()
            except Exception as e:
                self._log_msg(i18n.t("error", e=e))
            time.sleep(SCAN_INTERVAL)

    def _fetch_and_add_gem(self, gem_name: str, divine_rate: float):
        self._log_msg(i18n.t("searching", gem_name=gem_name))
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
            self._log_msg(i18n.t("not_found", gem_name=gem_name))

    def _on_close(self):
        self._running = False
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
