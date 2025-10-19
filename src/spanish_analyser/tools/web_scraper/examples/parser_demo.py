#!/usr/bin/env python3
"""Демо работы парсера practicatest.com"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tools.web_scraper import PracticaTestAuth, PracticaTestParser  # noqa: E402


def main():
    auth = PracticaTestAuth()
    try:
        if not auth.login():
            print("❌ Авторизация не удалась")
            return 1
        parser = PracticaTestParser(auth.session)
        print("🔎 Перехожу на страницу тестов:", parser.navigate_to_tests_page())
        data = parser.parse_tests_data()
        print(f"📋 Найдено записей: {len(data)}")
        return 0
    finally:
        auth.close()


if __name__ == "__main__":
    raise SystemExit(main())





