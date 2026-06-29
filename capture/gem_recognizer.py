"""
Виявляє вікно вибору каменів на екрані,
витягує 3 іконки каменів і розпізнає їх через icon_db.
"""
import cv2
import numpy as np
from PIL import Image
import pytesseract
import os

# Мінімальна оцінка збігу (0-1) для впевненого розпізнавання
MATCH_THRESHOLD = 0.60

# Розміри вікна вибору каменів (відносні до розміру регіону)
# 3 камені розташовані горизонтально, приблизно на 1/6, 1/2, 5/6 ширини
GEM_POSITIONS_REL = [0.26, 0.50, 0.74]   # відносна X позиція центру кожного каменя
GEM_Y_REL = 0.37                           # відносна Y позиція центру каменів
GEM_CROP_REL = 0.19                        # відносний розмір зовнішньої рамки


def pil_to_cv(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def detect_gem_window(cv_image: np.ndarray) -> bool:
    """
    Перевіряє чи відкрите вікно вибору каменів.
    Шукає золоті/коричневі пікселі рамки.
    """
    hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
    # Широкий діапазон: золотий, коричневий, бронзовий
    lower_gold = np.array([10, 40, 40])
    upper_gold = np.array([45, 255, 255])
    mask = cv2.inRange(hsv, lower_gold, upper_gold)
    gold_ratio = np.sum(mask > 0) / mask.size
    return gold_ratio > 0.005  # 0.5% — дуже м'який поріг


def extract_gem_regions(cv_image: np.ndarray) -> list:
    """
    Витягує 3 іконки каменів з зображення вікна.
    Повертає список з 3 numpy arrays (або None якщо не вдалось).
    """
    h, w = cv_image.shape[:2]
    gem_size = int(w * GEM_CROP_REL)
    gem_y = int(h * GEM_Y_REL)
    half = gem_size // 2

    regions = []
    for rel_x in GEM_POSITIONS_REL:
        cx = int(w * rel_x)
        x1 = max(0, cx - half)
        y1 = max(0, gem_y - half)
        x2 = min(w, cx + half)
        y2 = min(h, gem_y + half)

        if x2 > x1 and y2 > y1:
            crop = cv_image[y1:y2, x1:x2]
            regions.append(crop)
        else:
            regions.append(None)

    return regions


def recognize_gems(cv_image: np.ndarray, icon_db: dict, price_db: dict) -> list:
    """
    Головна функція: аналізує зображення вікна і повертає список каменів з цінами.
    Повертає: [{"name": str, "divine": float, "chaos": float, "is_best": bool, "slot": int}]
    або [] якщо вікно не виявлено.
    """
    if not detect_gem_window(cv_image):
        return []

    gem_regions = extract_gem_regions(cv_image)
    results = []

    for slot, region in enumerate(gem_regions):
        if region is None or region.size == 0:
            continue

        from core.icon_db import match_icon
        matches = match_icon(region, icon_db, top_n=1)

        if not matches:
            continue

        best_match = matches[0]
        if best_match["score"] < MATCH_THRESHOLD:
            continue

        norm_name = best_match["name"]
        gem_data = price_db.get(norm_name)
        if not gem_data:
            continue

        results.append({
            "name": gem_data["name"],
            "divine": gem_data["divine"],
            "chaos": gem_data["chaos"],
            "score": best_match["score"],
            "slot": slot,
            "is_best": False,
        })

    if not results:
        return []

    # Позначаємо найдорожчий
    best_idx = max(range(len(results)), key=lambda i: results[i]["divine"])
    results[best_idx]["is_best"] = True

    return results


def save_debug_crops(cv_image: np.ndarray, output_dir: str = "."):
    """Зберігає вирізані регіони для налагодження."""
    regions = extract_gem_regions(cv_image)
    for i, region in enumerate(regions):
        if region is not None:
            path = os.path.join(output_dir, f"debug_gem_{i+1}.png")
            cv2.imwrite(path, region)
            print(f"[debug] Збережено: {path}")


# --- Тест ---
if __name__ == "__main__":
    import sys
    from core.price_fetcher import fetch_prices
    from core.icon_db import load_icon_db
    from PIL import Image

    if len(sys.argv) < 2:
        print("Використання: python gem_recognizer.py <шлях_до_скріншоту>")
        exit()

    screenshot_path = sys.argv[1]
    img = Image.open(screenshot_path)
    cv_img = pil_to_cv(img)

    print("Завантажую ціни та іконки...")
    prices = fetch_prices()
    icons = load_icon_db()

    print(f"Аналізую скріншот...")
    save_debug_crops(cv_img)

    results = recognize_gems(cv_img, icons, prices)

    if results:
        print(f"\nЗнайдено {len(results)} каменів:")
        for gem in results:
            marker = " ← НАЙКРАЩИЙ" if gem["is_best"] else ""
            print(f"  Слот {gem['slot']+1}: {gem['name']:<50} {gem['divine']:.2f}d  (score={gem['score']:.2f}){marker}")
    else:
        print("Вікно вибору каменів не виявлено або камені не розпізнані")
        print("Збережено debug_gem_1/2/3.png для перевірки")
