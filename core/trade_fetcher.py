"""
Отримує реальні ціни каменів з офіційного PoE Trade API.
Запитує ціну тільки для конкретного каменя, не всіх 190 одразу.
Кешує результати на 10 хвилин.
"""
import time
import threading
import requests

LEAGUE = "Mirage"

_DEFAULT_LEAGUES = [
    "Mirage",
    "Standard",
    "Hardcore Mirage",
    "Solo Self-Found Mirage",
    "Hardcore",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "*/*",
}

CACHE_TTL = 600  # 10 хвилин

_cache: dict = {}
_lock = threading.Lock()
_divine_chaos: float = 0.0
_divine_ts: float = 0.0


def fetch_leagues() -> list[str]:
    """Повертає список активних PoE 1 ліг з офіційного API."""
    try:
        url = "https://api.pathofexile.com/leagues?type=main&realm=pc"
        r = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=8)
        r.raise_for_status()
        names = [lg["id"] for lg in r.json()]
        return names if names else _DEFAULT_LEAGUES
    except Exception:
        return _DEFAULT_LEAGUES


def _fetch_divine_rate(league: str) -> float:
    """Курс Divine Orb у chaos з poe.ninja."""
    global _divine_chaos, _divine_ts
    now = time.time()
    if _divine_chaos and now - _divine_ts < CACHE_TTL:
        return _divine_chaos
    try:
        url = f"https://poe.ninja/poe1/api/economy/exchange/current/overview?league={league}&type=Currency"
        r = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=10)
        for entry in r.json().get("lines", []):
            if entry.get("currencyTypeName") == "Divine Orb":
                rate = entry.get("chaosEquivalent", 0)
                if rate > 0:
                    _divine_chaos = rate
                    _divine_ts = now
                    return rate
    except Exception:
        pass
    return _divine_chaos or 570.0  # fallback


def _to_chaos(amount: float, currency: str, divine_rate: float) -> float:
    """Конвертує ціну в chaos."""
    if currency == "chaos":
        return amount
    if currency == "divine":
        return amount * divine_rate
    if currency == "exalted":
        return amount * 100  # приблизно
    if currency == "mirror":
        return amount * 200000
    return 0.0


def fetch_gem_price(gem_name: str, league: str = None) -> dict | None:
    """
    Повертає ціну каменя з trade API.
    dict: {"name": str, "chaos": float, "divine": float, "listings": int}
    або None якщо не знайдено.
    """
    league = league or LEAGUE
    cache_key = f"{league}::{gem_name.lower()}"

    with _lock:
        cached = _cache.get(cache_key)
        if cached and time.time() - cached["ts"] < CACHE_TTL:
            return cached["data"]

    try:
        divine_rate = _fetch_divine_rate(league)

        # Крок 1: Знайти лістинги каменя
        search_url = f"https://www.pathofexile.com/api/trade/search/{league}"
        def build_query(status: str) -> dict:
            return {
                "query": {
                    "status": {"option": status},
                    "term": gem_name,
                    "stats": [{"type": "and", "filters": []}],
                    "filters": {
                        "misc_filters": {
                            "filters": {
                                "gem_level": {"min": 1, "max": 1},
                                "corrupted": {"option": "false"},
                            }
                        }
                    },
                },
                "sort": {"price": "asc"},
            }

        r = requests.post(search_url, json=build_query("online"), headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return None

        data = r.json()
        total = data.get("total", 0)
        ids = data.get("result", [])

        # Якщо мало онлайн лістингів — беремо і офлайн
        if len(ids) < 5:
            r2 = requests.post(search_url, json=build_query("any"), headers=HEADERS, timeout=12)
            if r2.status_code == 200:
                data = r2.json()
                total = data.get("total", 0)
                ids = data.get("result", [])

        if not ids:
            return None

        # Крок 2: Отримати реальні ціни (перші 10 найдешевших)
        fetch_ids = ids[:10]
        qid = data.get("id", "")
        fetch_url = f"https://www.pathofexile.com/api/trade/fetch/{','.join(fetch_ids)}?query={qid}"
        r3 = requests.get(fetch_url, headers=HEADERS, timeout=12)
        if r3.status_code != 200:
            return None

        items = r3.json().get("result", [])
        prices_chaos = []
        for item in items:
            price = item.get("listing", {}).get("price", {})
            amount = price.get("amount", 0)
            currency = price.get("currency", "")
            if amount > 0 and currency:
                chaos_val = _to_chaos(amount, currency, divine_rate)
                if chaos_val > 0:
                    prices_chaos.append(chaos_val)

        if not prices_chaos:
            return None

        prices_chaos.sort()
        # Беремо медіану нижньої половини (реалістична ціна, без аутлайєрів)
        low_half = prices_chaos[:max(1, len(prices_chaos) // 2 + 1)]
        chaos_price = low_half[len(low_half) // 2]
        divine_price = chaos_price / divine_rate if divine_rate else 0

        result = {
            "name": gem_name,
            "chaos": round(chaos_price, 1),
            "divine": round(divine_price, 3),
            "listings": total,
        }

        with _lock:
            _cache[cache_key] = {"data": result, "ts": time.time()}

        return result

    except Exception as e:
        print(f"[trade] Помилка для {gem_name!r}: {e}")
        return None


# --- Тест ---
if __name__ == "__main__":
    gems = [
        "Blink Arrow of Prismatic Clones",
        "Fireball of Combusting",
        "Spark of the Nova",
    ]
    rate = _fetch_divine_rate(LEAGUE)
    print(f"Divine Orb = {rate:.0f}c\n")

    for name in gems:
        print(f"Шукаю: {name}...")
        result = fetch_gem_price(name)
        if result:
            print(f"  {result['chaos']:.0f}c / {result['divine']:.2f}d  ({result['listings']} listings)")
        else:
            print(f"  Не знайдено")
