import tkinter as tk
import ctypes
import ctypes.wintypes
import threading
import config

GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

COLOR_BG    = "#1a1a1a"
COLOR_DRAG  = "#1a1a3a"
COLOR_TEXT  = "#e0e0e0"
COLOR_BEST  = "#FFD700"
COLOR_PRICE = "#aaffaa"
COLOR_TITLE = "#c9a96e"   # золотистий для шапки
COLOR_DIM   = "#555555"   # для підзаголовка


def _is_poe_focused() -> bool:
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return False
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
        return "Path of Exile" in buf.value
    except Exception:
        return False


def _cursor_pos() -> tuple[int, int]:
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


class GemOverlay:
    def __init__(self):
        self._root            = None
        self._thread          = None
        self._lock            = threading.Lock()
        self._pending_results = None
        self._has_content     = False
        self._drag_mode       = False
        self._poe_focused     = False
        self._hovering        = False
        self._gem_count       = 0
        self._drag_x          = 0
        self._drag_y          = 0

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        self._root = tk.Tk()
        self._root.title("PoE Gem Overlay")
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.92)
        self._root.configure(bg=COLOR_BG)
        self._root.geometry(f"320x40+{config.OVERLAY_X}+{config.OVERLAY_Y}")
        self._root.withdraw()

        self._make_click_through()

        self._frame = tk.Frame(self._root, bg=COLOR_BG, padx=8, pady=4)
        self._frame.pack(fill=tk.BOTH, expand=True)

        # Шапка — прихована за замовчуванням, з'являється при наведенні
        self._header_frame = tk.Frame(self._frame, bg=COLOR_BG)
        self._header_title = tk.Label(
            self._header_frame,
            text="⚗  PoE Gem Prices",
            font=("Consolas", 10, "bold"),
            fg=COLOR_TITLE, bg=COLOR_BG, anchor="w",
        )
        self._header_title.pack(side=tk.LEFT)
        tk.Label(
            self._header_frame,
            text="poe.trade",
            font=("Consolas", 8),
            fg=COLOR_DIM, bg=COLOR_BG, anchor="e",
        ).pack(side=tk.RIGHT)
        # НЕ пакуємо _header_frame — він захований

        self._gems_frame = tk.Frame(self._frame, bg=COLOR_BG)
        self._gems_frame.pack(fill=tk.BOTH, expand=True)

        self._root.after(100, self._check_updates)
        self._root.after(150, self._check_hover)
        self._root.after(500, self._check_poe_focus)
        self._root.mainloop()

    # ------------------------------------------------------------------ Windows API

    def _make_click_through(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self._root.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            )
        except Exception as e:
            print(f"[overlay] click-through failed: {e}")

    def _remove_click_through(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self._root.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, (style & ~WS_EX_TRANSPARENT) | WS_EX_LAYERED
            )
        except Exception as e:
            print(f"[overlay] remove click-through failed: {e}")

    # ------------------------------------------------------------------ Hover (шапка)

    def _check_hover(self):
        if not self._drag_mode and self._root.winfo_ismapped():
            cx, cy = _cursor_pos()
            x  = self._root.winfo_x()
            y  = self._root.winfo_y()
            w  = self._root.winfo_width()
            h  = self._root.winfo_height()
            hovering = (x <= cx <= x + w) and (y <= cy <= y + h)
            if hovering != self._hovering:
                self._hovering = hovering
                self._update_header()
        self._root.after(150, self._check_hover)

    def _update_header(self):
        show = self._hovering or self._drag_mode
        if show:
            self._header_frame.pack(fill=tk.X, before=self._gems_frame)
        else:
            self._header_frame.pack_forget()
        self._recalc_height()

    def _recalc_height(self):
        self._root.update_idletasks()
        h = self._root.winfo_reqheight()
        x = self._root.winfo_x()
        y = self._root.winfo_y()
        self._root.geometry(f"320x{max(h, 30)}+{x}+{y}")

    # ------------------------------------------------------------------ PoE detection

    def _check_poe_focus(self):
        focused = _is_poe_focused()
        if focused != self._poe_focused:
            self._poe_focused = focused
            if not self._drag_mode:
                self._apply_visibility()
        self._root.after(500, self._check_poe_focus)

    def _apply_visibility(self):
        should_show = self._drag_mode or (self._poe_focused and self._has_content)
        if should_show:
            self._root.deiconify()
        else:
            self._root.withdraw()

    # ------------------------------------------------------------------ Drag

    def unlock(self):
        if self._root:
            self._root.after(0, self._do_unlock)

    def _do_unlock(self):
        self._drag_mode = True
        self._remove_click_through()
        self._root.configure(bg=COLOR_DRAG)
        self._frame.configure(bg=COLOR_DRAG)
        self._header_frame.configure(bg=COLOR_DRAG)
        for child in self._header_frame.winfo_children():
            child.configure(bg=COLOR_DRAG)
        self._header_title.configure(text="✥  Drag to move  ✥", fg="#6688ff")
        self._update_header()
        self._root.deiconify()
        for w in (self._root, self._frame, self._header_frame, self._gems_frame):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_motion)
            w.configure(cursor="fleur")

    def lock(self):
        if self._root:
            self._root.after(0, self._do_lock)

    def _do_lock(self):
        config.OVERLAY_X = self._root.winfo_x()
        config.OVERLAY_Y = self._root.winfo_y()
        self._drag_mode = False
        self._make_click_through()
        self._root.configure(bg=COLOR_BG)
        self._frame.configure(bg=COLOR_BG)
        self._header_frame.configure(bg=COLOR_BG)
        for child in self._header_frame.winfo_children():
            child.configure(bg=COLOR_BG)
        self._header_title.configure(text="⚗  PoE Gem Prices", fg=COLOR_TITLE)
        for w in (self._root, self._frame, self._header_frame, self._gems_frame):
            w.unbind("<ButtonPress-1>")
            w.unbind("<B1-Motion>")
            w.configure(cursor="")
        self._hovering = False
        self._update_header()
        self._apply_visibility()

    def _drag_start(self, event):
        self._drag_x = event.x_root - self._root.winfo_x()
        self._drag_y = event.y_root - self._root.winfo_y()

    def _drag_motion(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self._root.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------ Render

    def _check_updates(self):
        with self._lock:
            results = self._pending_results
            self._pending_results = None
        if results is not None:
            self._render(results)
        if self._root:
            self._root.after(100, self._check_updates)

    def _render(self, results: list):
        for widget in self._gems_frame.winfo_children():
            widget.destroy()

        self._has_content = bool(results)
        self._gem_count   = len(results)

        for gem in results:
            row = tk.Frame(self._gems_frame, bg=COLOR_BG)
            row.pack(fill=tk.X, pady=1)

            color  = COLOR_BEST if gem["is_best"] else COLOR_TEXT
            prefix = "★ " if gem["is_best"] else "  "

            tk.Label(
                row,
                text=f"{prefix}{gem['name']}",
                font=("Consolas", 10, "bold" if gem["is_best"] else "normal"),
                fg=color, bg=COLOR_BG, anchor="w",
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

            price_text = f"{gem['divine']:.2f}d" if gem["divine"] >= 0.01 else f"{gem['chaos']:.0f}c"
            tk.Label(
                row,
                text=price_text,
                font=("Consolas", 10, "bold"),
                fg=COLOR_BEST if gem["is_best"] else COLOR_PRICE,
                bg=COLOR_BG, anchor="e", width=8,
            ).pack(side=tk.RIGHT)

        self._recalc_height()
        if not self._drag_mode:
            self._apply_visibility()

    # ------------------------------------------------------------------ Public API

    def update(self, results: list):
        with self._lock:
            self._pending_results = results

    def clear(self):
        self.update([])

    def show(self):
        if self._root:
            self._root.after(0, self._root.deiconify)

    def hide(self):
        if self._root:
            self._root.after(0, self._root.withdraw)
