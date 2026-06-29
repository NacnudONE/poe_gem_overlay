"""
Завантажує іконки Transfigured Gems з poe.watch і зберігає локально.
Надає функцію match() для порівняння іконки з екрану з базою.
"""
import os
import sys
import json
import requests
import cv2
import numpy as np
from PIL import Image
import io
import config

def _icons_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "icons")
    # core/icon_db.py → піднімаємось на рівень вище до кореня проекту
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")

ICONS_DIR = _icons_dir()
INDEX_FILE = os.path.join(ICONS_DIR, "index.json")
ICON_SIZE = 64  # пікселі, до яких масштабуємо всі іконки

HEADERS = {
    "User-Agent": "Mozilla/5.0 Chrome/126.0.0.0",
    "Accept": "application/json",
}


def _normalize(name: str) -> str:
    return name.strip().lower()


def download_icons(price_db: dict, progress_callback=None) -> int:
    """
    Завантажує іконки для всіх каменів з price_db.
    Повертає кількість завантажених іконок.
    """
    os.makedirs(ICONS_DIR, exist_ok=True)

    # Отримуємо icon URLs з poe.watch
    url = f"https://api.poe.watch/compact?category=7&league={config.LEAGUE.replace(' ', '+')}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        all_gems = r.json().get("items", [])
    except Exception as e:
        print(f"[icon_db] Помилка завантаження списку: {e}")
        return 0

    # Будуємо словник name→icon_url тільки для наших transfigured gems
    icon_map = {}
    for gem in all_gems:
        name = gem.get("name", "")
        icon_url = gem.get("icon", "")
        norm = _normalize(name)
        if norm in price_db and icon_url:
            icon_map[norm] = {"url": icon_url, "name": name}

    index = {}
    downloaded = 0
    total = len(icon_map)

    for i, (norm_name, info) in enumerate(icon_map.items()):
        safe_name = norm_name.replace(" ", "_").replace("/", "_")
        icon_path = os.path.join(ICONS_DIR, f"{safe_name}.png")

        if progress_callback:
            progress_callback(i + 1, total, info["name"])

        # Пропускаємо якщо вже завантажено
        if os.path.exists(icon_path):
            index[norm_name] = icon_path
            downloaded += 1
            continue

        try:
            r = requests.get(info["url"], timeout=10)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            img = img.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
            img.save(icon_path)
            index[norm_name] = icon_path
            downloaded += 1
        except Exception as e:
            print(f"[icon_db] Не вдалось завантажити {info['name']}: {e}")

    # Зберігаємо індекс
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[icon_db] Готово: {downloaded}/{total} іконок")
    return downloaded


def load_icon_db() -> dict:
    """
    Завантажує іконки в пам'ять як numpy arrays для OpenCV.
    Повертає {norm_name: np.ndarray}
    """
    if not os.path.exists(INDEX_FILE):
        return {}

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    db = {}
    for norm_name, icon_path in index.items():
        if os.path.exists(icon_path):
            img = cv2.imread(icon_path, cv2.IMREAD_COLOR)
            if img is not None:
                img = cv2.resize(img, (ICON_SIZE, ICON_SIZE))
                db[norm_name] = img

    print(f"[icon_db] Завантажено {len(db)} іконок в пам'ять")
    return db


def _compute_hist(img: np.ndarray) -> np.ndarray:
    """Обчислює нормалізовану HSV гістограму, ігноруючи темні пікселі (фон/рамка)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Маскуємо темні пікселі (Value < 40) — це фон і рамка
    mask = hsv[:, :, 2] > 40
    mask_u8 = mask.astype(np.uint8) * 255

    # Гістограма по H (0-179) і S (0-255) — ігноруємо яскравість
    h_hist = cv2.calcHist([hsv], [0], mask_u8, [36], [0, 180])
    s_hist = cv2.calcHist([hsv], [1], mask_u8, [32], [0, 256])

    combined = np.concatenate([h_hist.flatten(), s_hist.flatten()])
    norm = np.linalg.norm(combined)
    return combined / norm if norm > 0 else combined


def match_icon(region: np.ndarray, icon_db: dict, top_n: int = 3) -> list:
    """
    Порівнює вирізаний регіон екрану з усіма іконками в базі через кольорові гістограми.
    Повертає топ-N найкращих збігів: [{"name": str, "score": float}]
    """
    if region is None or region.size == 0 or not icon_db:
        return []

    region_resized = cv2.resize(region, (ICON_SIZE, ICON_SIZE))
    region_hist = _compute_hist(region_resized)

    scores = []
    for norm_name, icon_img in icon_db.items():
        icon_hist = _compute_hist(icon_img)
        # Косинусна схожість гістограм
        score = float(np.dot(region_hist, icon_hist))
        scores.append((norm_name, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return [{"name": norm_name, "score": score} for norm_name, score in scores[:top_n]]


# --- Тест ---
if __name__ == "__main__":
    from core.price_fetcher import fetch_prices

    print("Завантажую ціни...")
    prices = fetch_prices()

    def show_progress(cur, total, name):
        print(f"  [{cur}/{total}] {name[:50]}", end="\r")

    print(f"\nЗавантажую іконки для {len(prices)} gems...")
    n = download_icons(prices, progress_callback=show_progress)
    print(f"\nГотово: {n} іконок")

    db = load_icon_db()
    print(f"В пам'яті: {len(db)} іконок")
