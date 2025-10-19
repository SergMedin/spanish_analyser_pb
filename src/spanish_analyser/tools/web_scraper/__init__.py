"""
Модуль для веб-скрапинга и загрузки HTML страниц

Предоставляет инструменты для:
- Загрузки HTML страниц с веб-сайтов
- Управления задержками между запросами
- Сохранения загруженного контента
- Обработки ошибок и повторных попыток
- Специализированные инструменты для билетов по вождению
"""

from .html_downloader import HTMLDownloader
from .scraping_manager import ScrapingManager
from .driving_tests_downloader import DrivingTestsDownloader, DrivingTestsScrapingManager
from .practicatest_auth import PracticaTestAuth
from .practicatest_parser import PracticaTestParser
# Экспортируем только ядро. Демо-скрипты вынесены в examples/
from .test_downloader import TestDownloader

__all__ = [
    "HTMLDownloader",
    "ScrapingManager",
    "DrivingTestsDownloader",
    "DrivingTestsScrapingManager",
    "PracticaTestAuth",
    "PracticaTestParser",
    "TestDownloader"
]
