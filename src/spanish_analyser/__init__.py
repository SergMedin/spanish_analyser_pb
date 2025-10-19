"""
Spanish Analyser - модуль для анализа испанского языка с интеграцией Anki

Этот модуль предоставляет инструменты для:
- Анализа испанских текстов
- Работы с коллекциями Anki
- Обработки и перевода испанских слов
- Создания карточек для изучения
- Веб-скрапинга тестов
- Создания Excel отчётов
"""

__version__ = "0.1.0"
__author__ = "Sergey"

from .text_processor import SpanishTextProcessor
from .word_analyzer import WordAnalyzer
from . import cli

__all__ = [
    "SpanishTextProcessor",
    "WordAnalyzer",
    "cli"
]
