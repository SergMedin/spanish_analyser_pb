"""
Инструменты Spanish Analyser

Этот модуль содержит основные инструменты проекта:
- web_scraper: Загрузка тестов с practicatest.com
- text_analyzer: Анализ текстов и создание Excel отчётов
- anki_deck_generator: Создание Anki колод
"""

__version__ = "0.1.0"

# Основные инструменты
__all__ = [
    "web_scraper",
    "text_analyzer", 
    "anki_deck_generator"
]
