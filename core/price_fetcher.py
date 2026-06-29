import requests
import threading
import config

_price_db = {}
_lock = threading.Lock()
_timer = None

POE_WATCH_URL = "https://api.poe.watch/compact?category=7&league={league}"
POE_NINJA_CURRENCY_URL = "https://poe.ninja/poe1/api/economy/exchange/current/overview?league={league}&type=Currency"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def _normalize(name: str) -> str:
    return name.strip().lower()


def _get_divine_rate(league: str) -> float:
    """Повертає ціну Divine Orb у chaos для конвертації."""
    try:
        url = POE_NINJA_CURRENCY_URL.format(league=league.replace(" ", "+"))
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        for item in r.json().get("lines", []):
            if item.get("id") == "divine":
                return float(item.get("primaryValue", 200))
    except Exception as e:
        print(f"[price_fetcher] Не вдалось отримати курс divine: {e}")
    return 200.0  # fallback


def fetch_prices() -> dict:
    """
    Завантажує ціни Transfigured Gems з poe.watch
    і повертає словник {нормалізована_назва: {name, divine, chaos}}.
    """
    league = config.LEAGUE
    divine_rate = _get_divine_rate(league)
    print(f"[price_fetcher] Divine Orb = {divine_rate:.1f} chaos ({league})")

    try:
        url = POE_WATCH_URL.format(league=league.replace(" ", "+"))
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        items = r.json().get("items", [])
    except Exception as e:
        print(f"[price_fetcher] Помилка завантаження з poe.watch: {e}")
        return {}

    result = {}
    for item in items:
        name = item.get("name", "")
        group = item.get("group", "")
        chaos_value = item.get("mean", 0.0)

        # Беремо тільки transfigured gems:
        # - назва містить " of " (без дужок — без support gem комбо)
        # - group = activegem, vaalgems, support, або supportgem
        if " of " not in name:
            continue
        if "(" in name or ")" in name:
            continue
        if group not in ("activegem", "vaalgems", "support", "supportgem"):
            continue
        if chaos_value <= 0:
            continue

        divine_value = round(chaos_value / divine_rate, 2)
        normalized_name = _normalize(name)

        # Якщо є дубль — залишаємо дорожчий
        if normalized_name in result and result[normalized_name]["chaos"] >= chaos_value:
            continue

        result[normalized_name] = {
            "name": name,
            "divine": divine_value,
            "chaos": round(chaos_value, 1),
        }

    print(f"[price_fetcher] Знайдено {len(result)} Transfigured Gems")
    return result


def refresh():
    """Оновлює базу цін і планує наступне оновлення."""
    global _price_db, _timer

    new_prices = fetch_prices()
    if new_prices:
        with _lock:
            _price_db = new_prices

    _timer = threading.Timer(config.REFRESH_INTERVAL, refresh)
    _timer.daemon = True
    _timer.start()


def get_prices() -> dict:
    """Повертає поточну базу цін (потокобезпечно)."""
    with _lock:
        return dict(_price_db)


def start():
    """Запускає завантаження цін і автооновлення."""
    refresh()


def stop():
    """Зупиняє автооновлення."""
    global _timer
    if _timer:
        _timer.cancel()


# --- Тест ---
if __name__ == "__main__":
    print(f"Завантажую ціни для ліги '{config.LEAGUE}'...")
    prices = fetch_prices()

    if not prices:
        print("Нічого не знайдено. Перевір config.LEAGUE")
    else:
        sorted_gems = sorted(prices.values(), key=lambda x: x["chaos"], reverse=True)
        print(f"\nТоп-15 найдорожчих Transfigured Gems:")
        for i, gem in enumerate(sorted_gems[:15], 1):
            print(f"  {i:2}. {gem['name']:<55} {gem['divine']:>7.2f}d  ({gem['chaos']:>8.0f}c)")
