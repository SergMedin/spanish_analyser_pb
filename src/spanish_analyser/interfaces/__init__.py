"""
Интерфейсы для компонентов анализа испанского текста.

Определяет абстрактные базовые классы для всех компонентов,
обеспечивая единообразный API и возможность замены реализаций.
"""

from .text_processor import (
    TextProcessor,
    TokenProcessorInterface,
    LemmaProcessorInterface,
    POSTaggerInterface,
    FrequencyAnalyzerInterface,
    WordComparatorInterface,
    WordNormalizerInterface,
    ResultExporterInterface
)

__all__ = [
    'TextProcessor',
    'TokenProcessorInterface',
    'LemmaProcessorInterface', 
    'POSTaggerInterface',
    'FrequencyAnalyzerInterface',
    'WordComparatorInterface',
    'WordNormalizerInterface',
    'ResultExporterInterface'
]
