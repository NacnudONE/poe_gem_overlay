import time
import threading
import keyboard
import config
from core import price_fetcher, gem_matcher
from capture import screen_capture, ocr_scanner
from ui.overlay import GemOverlay

# Мінімальна яскравість регіону щоб вважати що UI відкритий
BRIGHTNESS_THRESHOLD = 60

# Затримка між скануваннями (секунд)
SCAN_INTERVAL = 0.5

_running = True
_overlay_enabled = True
_overlay = GemOverlay()


def toggle_overlay():
    """Перемикає overlay гарячою клавішею."""
    global _overlay_enabled
    _overlay_enabled = not _overlay_enabled
    if _overlay_enabled:
        _overlay.show()
        print(f"[main] Overlay увімкнено ({config.HOTKEY})")
    else:
        _overlay.hide()
        print(f"[main] Overlay вимкнено ({config.HOTKEY})")


def scan_loop(region: tuple):
    """Головний цикл сканування."""
    x, y, w, h = region
    last_had_results = False

    print("[main] Сканування запущено. Наведи камеру на екран вибору каменів у лабіринті.")

    while _running:
        try:
            img = screen_capture.capture_region(x, y, w, h)
            brightness = ocr_scanner.get_brightness(img)

            # Якщо регіон занадто темний — UI швидше за все закритий
            if brightness < BRIGHTNESS_THRESHOLD:
                if last_had_results:
                    _overlay.clear()
                    last_had_results = False
                time.sleep(SCAN_INTERVAL)
                continue

            # Запускаємо OCR
            lines = ocr_scanner.scan(img)

            if not lines:
                if last_had_results:
                    _overlay.clear()
                    last_had_results = False
                time.sleep(SCAN_INTERVAL)
                continue

            # Шукаємо ціни
            prices = price_fetcher.get_prices()
            results = gem_matcher.match(lines, prices)

            if results:
                _overlay.update(results)
                last_had_results = True

                # Виводимо в консоль для налагодження
                best = next((g for g in results if g["is_best"]), None)
                if best:
                    print(f"[scan] Найкращий: {best['name']} — {best['divine']:.2f} divine")
            else:
                if last_had_results:
                    _overlay.clear()
                    last_had_results = False

        except Exception as e:
            print(f"[main] Помилка в циклі сканування: {e}")

        time.sleep(SCAN_INTERVAL)


def main():
    print("=" * 50)
    print("  PoE Gem Price Overlay")
    print(f"  Ліга: {config.LEAGUE}")
    print(f"  Гаряча клавіша: {config.HOTKEY} — вкл/викл overlay")
    print("=" * 50)

    # Запускаємо overlay
    _overlay.start()
    time.sleep(0.3)

    # Завантажуємо ціни (у фоні)
    print("\n[main] Завантажую ціни з poe.ninja...")
    price_fetcher.start()

    # Чекаємо поки ціни завантажаться
    timeout = 15
    while not price_fetcher.get_prices() and timeout > 0:
        time.sleep(1)
        timeout -= 1

    prices = price_fetcher.get_prices()
    if not prices:
        print("[main] УВАГА: Ціни не завантажились. Перевір config.LEAGUE і інтернет-з'єднання.")
    else:
        print(f"[main] Завантажено {len(prices)} Transfigured Gems")

    # Калібрування регіону
    region = screen_capture.get_or_calibrate()
    if not region:
        print("[main] Регіон не обраний. Виходжу.")
        return

    # Реєструємо гарячу клавішу
    keyboard.add_hotkey(config.HOTKEY, toggle_overlay)
    print(f"\n[main] Натисни {config.HOTKEY} щоб вкл/викл overlay")
    print("[main] Натисни Ctrl+C щоб вийти\n")

    # Запускаємо головний цикл у фоновому потоці
    scan_thread = threading.Thread(target=scan_loop, args=(region,), daemon=True)
    scan_thread.start()

    # Тримаємо головний потік живим
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        global _running
        _running = False
        price_fetcher.stop()
        print("\n[main] Завершення роботи.")


if __name__ == "__main__":
    main()
