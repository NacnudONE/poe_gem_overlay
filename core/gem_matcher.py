import difflib
import config


def _normalize(text: str) -> str:
    return text.strip().lower()


def match(ocr_lines: list[str], price_db: dict) -> list[dict]:
    """
    Співставляє рядки OCR з базою цін.

    ocr_lines  — список рядків тексту з екрану
    price_db   — словник {нормалізована_назва: {name, divine, chaos}}

    Повертає список знайдених каменів:
    [{"name": str, "divine": float, "chaos": float, "is_best": bool}]
    """
    if not price_db or not ocr_lines:
        return []

    db_keys = list(price_db.keys())
    results = []

    for line in ocr_lines:
        normalized_line = _normalize(line)

        # Шукаємо найближчу назву через difflib
        matches = difflib.get_close_matches(
            normalized_line,
            db_keys,
            n=1,
            cutoff=config.MATCH_THRESHOLD,
        )

        if matches:
            best_key = matches[0]
            gem_data = price_db[best_key]
            results.append({
                "name": gem_data["name"],
                "divine": gem_data["divine"],
                "chaos": gem_data["chaos"],
                "is_best": False,
            })

    if not results:
        return []

    # Видаляємо дублікати (один камінь може з'явитись кілька разів)
    seen = set()
    unique_results = []
    for item in results:
        if item["name"] not in seen:
            seen.add(item["name"])
            unique_results.append(item)

    # Позначаємо найдорожчий
    best_idx = max(range(len(unique_results)), key=lambda i: unique_results[i]["divine"])
    unique_results[best_idx]["is_best"] = True

    # Сортуємо від найдорожчого до найдешевшого
    unique_results.sort(key=lambda x: x["divine"], reverse=True)

    return unique_results


# --- Тест ---
if __name__ == "__main__":
    from core.price_fetcher import fetch_prices

    print("Завантажую ціни...")
    db = fetch_prices()

    if not db:
        print("База цін порожня. Перевір config.LEAGUE")
        exit()

    # Симулюємо OCR-рядки з типовими помилками розпізнавання
    test_lines = [
        "Fireball of Combusting",
        "Flameblast of Contraction",
        "Spark of Noxious Propagation",
        "SomethingThatDoesntExist",
        "Firebail of Combustng",  # з OCR-помилками
    ]

    print(f"\nTesting з {len(test_lines)} рядками OCR:")
    results = match(test_lines, db)

    if results:
        for gem in results:
            marker = " ← НАЙКРАЩИЙ" if gem["is_best"] else ""
            print(f"  {gem['name']:<45} {gem['divine']:>6.2f} div{marker}")
    else:
        print("  Жодного збігу не знайдено")
