"""
Компоненты для анализа испанского текста.

Каждый компонент отвечает за одну конкретную задачу:
- TokenProcessor - токенизация текста
- LemmaProcessor - лемматизация слов
- POSTagger - определение частей речи
- FrequencyAnalyzer - подсчёт частотности
- WordComparator - сравнение с известными словами
- WordNormalizer - нормализация слов
- ResultExporter - экспорт результатов
"""

from .tokenizer import TokenProcessor
from .lemmatizer import LemmaProcessor
from .pos_tagger import POSTagger
from .frequency_analyzer import FrequencyAnalyzer
from .word_comparator import WordComparator
from .normalizer import WordNormalizer
from .exporter import ResultExporter
from .text_pipeline import SpanishTextPipeline, TokenInfo, TextAnalysisContext

__all__ = [
    'TokenProcessor',
    'LemmaProcessor', 
    'POSTagger',
    'FrequencyAnalyzer',
    'WordComparator',
    'WordNormalizer',
    'ResultExporter',
    'SpanishTextPipeline',
    'TokenInfo',
    'TextAnalysisContext',
]
