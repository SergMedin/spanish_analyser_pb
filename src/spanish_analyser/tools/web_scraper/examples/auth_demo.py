#!/usr/bin/env python3
"""Демо авторизации practicatest.com"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tools.web_scraper import PracticaTestAuth, DrivingTestsDownloader  # noqa: E402


def main():
    auth = PracticaTestAuth()
    try:
        print("🔐 Проверяю авторизацию...")
        if not auth.login():
            print("❌ Авторизация не удалась")
            return 1
        print("✅ Авторизация успешна")

        downloader = DrivingTestsDownloader()
        print("🔍 Статус авторизации загрузчика:", downloader.get_auth_status())
        return 0
    finally:
        auth.close()


if __name__ == "__main__":
    raise SystemExit(main())





