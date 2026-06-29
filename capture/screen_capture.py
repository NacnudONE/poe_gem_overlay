import mss
import mss.tools
from PIL import Image
import tkinter as tk
import config


def capture_region(x: int, y: int, w: int, h: int) -> Image.Image:
    """Знімає прямокутну ділянку екрану і повертає PIL Image."""
    with mss.mss() as sct:
        monitor = {"top": y, "left": x, "width": w, "height": h}
        screenshot = sct.grab(monitor)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")


def calibrate() -> tuple:
    """
    Відкриває прозоре вікно для вибору регіону.
    Користувач натискає і тягне мишу щоб обрати ділянку.
    Повертає (x, y, w, h).
    """
    result = {}

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.attributes("-topmost", True)
    root.configure(bg="blue")

    canvas = tk.Canvas(root, cursor="cross", bg="blue", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    label = tk.Label(
        root,
        text="Натисни і тягни мишею щоб вибрати регіон з каменями.\nВідпусти щоб підтвердити. ESC — скасувати.",
        font=("Arial", 16, "bold"),
        bg="blue",
        fg="white",
    )
    label.place(relx=0.5, rely=0.05, anchor="center")

    start_x = start_y = 0
    rect_id = None

    def on_press(event):
        nonlocal start_x, start_y, rect_id
        start_x, start_y = event.x, event.y
        if rect_id:
            canvas.delete(rect_id)

    def on_drag(event):
        nonlocal rect_id
        if rect_id:
            canvas.delete(rect_id)
        rect_id = canvas.create_rectangle(
            start_x, start_y, event.x, event.y,
            outline="red", width=3
        )

    def on_release(event):
        x1, y1 = min(start_x, event.x), min(start_y, event.y)
        x2, y2 = max(start_x, event.x), max(start_y, event.y)
        result["region"] = (x1, y1, x2 - x1, y2 - y1)
        root.destroy()

    def on_escape(event):
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", on_escape)

    root.mainloop()

    region = result.get("region")
    if region and region[2] > 10 and region[3] > 10:
        print(f"[screen_capture] Регіон: {region}")
        return region

    print("[screen_capture] Калібрування скасовано або регіон занадто малий")
    return None


def get_or_calibrate() -> tuple:
    """Повертає збережений регіон або запускає калібрування."""
    if config.SCAN_REGION:
        return config.SCAN_REGION
    region = calibrate()
    if region:
        # Зберігаємо в config для поточної сесії
        config.SCAN_REGION = region
    return region


# --- Тест ---
if __name__ == "__main__":
    print("Запуск калібрування...")
    region = calibrate()
    if region:
        x, y, w, h = region
        print(f"Захоплюю регіон {region}...")
        img = capture_region(x, y, w, h)
        img.save("test_capture.png")
        print("Збережено як test_capture.png")
