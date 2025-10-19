"""
Абстрактные интерфейсы для компонентов анализа испанского текста.

Определяет контракты, которые должны реализовывать все компоненты,
обеспечивая единообразный API и возможность замены реализаций.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WordInfo:
    """Информация о слове для изучения."""
    word: str
    pos_tag: str
    pos_tag_ru: str
    frequency: int
    lemma: str
    is_known: bool = False
    context_examples: Optional[List[str]] = None
    # Дополнительные комментарии для экспорта (подсказки по совпадениям в ANKI и пр.)
    comment: Optional[str] = None
    # Род (по данным spaCy), например 'Masc', 'Fem', 'Common', 'Neut', 'Unknown'
    gender: Optional[str] = None


@dataclass
class AnalysisResult:
    """Результат анализа текста."""
    words: List[WordInfo]
    frequency_dict: Dict[str, int]
    unknown_words: List[str]
    total_words: int
    unique_words: int
    processing_time: float
    metadata: Optional[Dict[str, Any]] = None


class TokenProcessorInterface(ABC):
    """Интерфейс для токенизации текста."""
    
    @abstractmethod
    def tokenize(self, text: str) -> List[str]:
        """Разбивает текст на токены."""
        pass
    
    @abstractmethod
    def is_valid_token(self, token: str) -> bool:
        """Проверяет валидность токена."""
        pass
    
    @abstractmethod
    def filter_tokens(self, tokens: List[str]) -> List[str]:
        """Фильтрует токены по критериям."""
        pass


class LemmaProcessorInterface(ABC):
    """Интерфейс для лемматизации слов."""
    
    @abstractmethod
    def lemmatize(self, word: str) -> str:
        """Приводит слово к базовой форме."""
        pass
    
    @abstractmethod
    def lemmatize_batch(self, words: List[str]) -> List[str]:
        """Приводит список слов к базовым формам."""
        pass


class POSTaggerInterface(ABC):
    """Интерфейс для определения частей речи."""
    
    @abstractmethod
    def get_pos_tags(self, words: List[str]) -> List[str]:
        """Определяет части речи для списка слов."""
        pass
    
    @abstractmethod
    def get_pos_tag_ru(self, pos_tag: str) -> str:
        """Переводит POS-тег на русский язык."""
        pass
    
    @abstractmethod
    def get_learning_priority(self, pos_tag: str) -> int:
        """Возвращает приоритет изучения для части речи."""
        pass


class FrequencyAnalyzerInterface(ABC):
    """Интерфейс для анализа частотности слов."""
    
    @abstractmethod
    def count_frequency(self, words: List[str]) -> Dict[str, int]:
        """Подсчитывает частоту появления слов."""
        pass
    
    @abstractmethod
    def get_most_frequent(self, n: int = 10) -> List[tuple[str, int]]:
        """Возвращает n самых частых слов."""
        pass
    
    @abstractmethod
    def reset_statistics(self) -> None:
        """Сбрасывает статистику."""
        pass


class WordComparatorInterface(ABC):
    """Интерфейс для сравнения слов с известными."""
    
    @abstractmethod
    def load_known_words(self, source: Union[str, Path, List[str]]) -> None:
        """Загружает известные слова из источника."""
        pass
    
    @abstractmethod
    def is_word_known(self, word: str) -> bool:
        """Проверяет, известно ли слово."""
        pass
    
    @abstractmethod
    def filter_unknown_words(self, words: List[str]) -> List[str]:
        """Фильтрует только неизвестные слова."""
        pass


class WordNormalizerInterface(ABC):
    """Интерфейс для нормализации слов."""
    
    @abstractmethod
    def normalize(self, word: str) -> str:
        """Нормализует слово для сравнения."""
        pass
    
    @abstractmethod
    def normalize_batch(self, words: List[str]) -> List[str]:
        """Нормализует список слов."""
        pass


class ResultExporterInterface(ABC):
    """Интерфейс для экспорта результатов."""
    
    @abstractmethod
    def export_to_excel(self, result: AnalysisResult, filepath: Union[str, Path]) -> None:
        """Экспортирует результат в Excel формат."""
        pass
    
    @abstractmethod
    def export_to_csv(self, result: AnalysisResult, filepath: Union[str, Path]) -> None:
        """Экспортирует результат в CSV формат для Anki."""
        pass
    
    @abstractmethod
    def export_to_json(self, result: AnalysisResult, filepath: Union[str, Path]) -> None:
        """Экспортирует результат в JSON формат."""
        pass


class TextProcessor(ABC):
    """Основной интерфейс для обработки текста."""
    
    @abstractmethod
    def analyze_text(self, text: str) -> AnalysisResult:
        """Анализирует текст и возвращает результат."""
        pass
    
    @abstractmethod
    def get_unknown_words_for_learning(self, result: AnalysisResult) -> List[WordInfo]:
        """Возвращает слова для изучения."""
        pass
