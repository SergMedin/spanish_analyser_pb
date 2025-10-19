#!/usr/bin/env python3
"""Демо реальной авторизации + доступ к защищённой странице"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tools.web_scraper import PracticaTestAuth  # noqa: E402


def main():
    auth = PracticaTestAuth()
    try:
        if not auth.login():
            print("❌ Авторизация не удалась")
            return 1
        info = auth.get_session_info()
        print("📊 Информация о сессии:", info)
        return 0
    finally:
        auth.close()


if __name__ == "__main__":
    raise SystemExit(main())





