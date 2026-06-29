_TRANSLATIONS = {
    "uk": {
        "move_overlay":    "📍 Перемістити overlay",
        "lock_overlay":    "🔒 Зафіксувати",
        "update_available": "🔔 Доступне оновлення {version}",
        "download_update":  "Завантажити",
        "downloading":      "⬇ Завантаження {pct}%",
        "download_done":    "✓ Збережено в Downloads",
        "open_folder":      "📂 Відкрити",
        "download_error":   "⚠ Помилка — спробуй вручну",
        "retry":            "↺ Ще раз",
        "settings":      " Налаштування ",
        "league":        "Ліга:",
        "hotkey":        "Клавіша:",
        "status":        " Статус ",
        "prices":        "Ціни:",
        "scanning":      "Сканування:",
        "log":           " Лог ",
        "start":         "▶  Старт",
        "stop":          "⏹  Стоп",
        "refresh":       "🔄  Оновити ціни",
        "clear":         "🗑  Очистити",
        "loading":       "Завантаження...",
        "ready":         "Готово  ✓",
        "stopped":       "Зупинено",
        "active":        "Активне  ●",
        "league_loaded": "Ліга: {league}. Ціни з PoE Trade API",
        "gems_cleared":  "Список каменів очищено",
        "scan_started":  "Сканування запущено — наводь мишу на камені!",
        "scan_stopped":  "Сканування зупинено",
        "error":         "Помилка: {e}",
        "searching":     "Шукаю: {gem_name}...",
        "not_found":     "  Не знайдено: {gem_name}",
    },
    "en": {
        "move_overlay":    "📍 Move overlay",
        "lock_overlay":    "🔒 Lock position",
        "update_available": "🔔 Update available {version}",
        "download_update":  "Download",
        "downloading":      "⬇ Downloading {pct}%",
        "download_done":    "✓ Saved to Downloads",
        "open_folder":      "📂 Open folder",
        "download_error":   "⚠ Error — try manually",
        "retry":            "↺ Retry",
        "settings":      " Settings ",
        "league":        "League:",
        "hotkey":        "Hotkey:",
        "status":        " Status ",
        "prices":        "Prices:",
        "scanning":      "Scanning:",
        "log":           " Log ",
        "start":         "▶  Start",
        "stop":          "⏹  Stop",
        "refresh":       "🔄  Refresh prices",
        "clear":         "🗑  Clear",
        "loading":       "Loading...",
        "ready":         "Ready  ✓",
        "stopped":       "Stopped",
        "active":        "Active  ●",
        "league_loaded": "League: {league}. Prices from PoE Trade API",
        "gems_cleared":  "Gem list cleared",
        "scan_started":  "Scanning started — hover over gems!",
        "scan_stopped":  "Scanning stopped",
        "error":         "Error: {e}",
        "searching":     "Looking up: {gem_name}...",
        "not_found":     "  Not found: {gem_name}",
    },
}

_lang = "uk"


def set_lang(lang: str):
    global _lang
    _lang = lang


def get_lang() -> str:
    return _lang


def t(key: str, **kwargs) -> str:
    text = _TRANSLATIONS.get(_lang, _TRANSLATIONS["uk"]).get(key, key)
    return text.format(**kwargs) if kwargs else text
