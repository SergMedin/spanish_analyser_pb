"""
Компонент для анализа частотности испанских слов.

Отвечает за подсчёт частоты появления слов, ведение статистики
и получение самых частых слов для изучения.
"""

from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
from ..interfaces.text_processor import FrequencyAnalyzerInterface


class FrequencyAnalyzer(FrequencyAnalyzerInterface):
    """Анализатор частотности слов."""
    
    def __init__(self):
        """Инициализирует анализатор частотности."""
        self._word_frequencies: Counter = Counter()
        self._document_frequencies: Dict[str, int] = defaultdict(int)
        self._total_documents = 0
        self._total_words = 0
        
        # Кэш для быстрого доступа к частым словам
        self._most_frequent_cache: Optional[List[Tuple[str, int]]] = None
        self._cache_dirty = True
    
    def count_frequency(self, words: List[str]) -> Dict[str, int]:
        """
        Подсчитывает частоту появления слов.
        
        Args:
            words: Список слов для анализа
            
        Returns:
            Словарь с частотой каждого слова
        """
        if not words:
            return {}
        
        # Подсчитываем частоту
        word_counts = Counter(words)
        
        # Обновляем общую статистику
        self._word_frequencies.update(word_counts)
        self._total_words += len(words)
        self._total_documents += 1
        
        # Помечаем кэш как устаревший
        self._cache_dirty = True
        
        return dict(word_counts)
    
    def get_most_frequent(self, n: int = 10) -> List[Tuple[str, int]]:
        """
        Возвращает n самых частых слов.
        
        Args:
            n: Количество слов для возврата
            
        Returns:
            Список кортежей (слово, частота)
        """
        if not self._word_frequencies:
            return []
        
        # Проверяем кэш
        if not self._cache_dirty and self._most_frequent_cache:
            return self._most_frequent_cache[:n]
        
        # Обновляем кэш
        self._most_frequent_cache = self._word_frequencies.most_common()
        self._cache_dirty = False
        
        return self._most_frequent_cache[:n]
    
    def reset_statistics(self) -> None:
        """Сбрасывает всю статистику."""
        self._word_frequencies.clear()
        self._document_frequencies.clear()
        self._total_documents = 0
        self._total_words = 0
        self._most_frequent_cache = None
        self._cache_dirty = True
    
    def get_word_frequency(self, word: str) -> int:
        """
        Возвращает частоту конкретного слова.
        
        Args:
            word: Слово для проверки
            
        Returns:
            Частота появления слова
        """
        return self._word_frequencies.get(word, 0)
    
    def get_frequency_statistics(self) -> Dict[str, int]:
        """
        Возвращает общую статистику частотности.
        
        Returns:
            Словарь со статистикой
        """
        if not self._word_frequencies:
            return {
                'total_words': 0,
                'unique_words': 0,
                'total_documents': 0,
                'avg_words_per_document': 0.0
            }
        
        return {
            'total_words': self._total_words,
            'unique_words': len(self._word_frequencies),
            'total_documents': self._total_documents,
            'avg_words_per_document': self._total_words / self._total_documents if self._total_documents > 0 else 0.0
        }
    
    def get_words_by_frequency_range(self, min_freq: int = 1, max_freq: Optional[int] = None) -> List[Tuple[str, int]]:
        """
        Возвращает слова в заданном диапазоне частотности.
        
        Args:
            min_freq: Минимальная частота
            max_freq: Максимальная частота (None = без ограничений)
            
        Returns:
            Список кортежей (слово, частота)
        """
        if not self._word_frequencies:
            return []
        
        filtered_words = []
        
        for word, freq in self._word_frequencies.items():
            if freq >= min_freq and (max_freq is None or freq <= max_freq):
                filtered_words.append((word, freq))
        
        # Сортируем по частоте (убывание)
        filtered_words.sort(key=lambda x: x[1], reverse=True)
        
        return filtered_words
    
    def get_rare_words(self, max_frequency: int = 3) -> List[Tuple[str, int]]:
        """
        Возвращает редкие слова (с частотой не выше указанной).
        
        Args:
            max_frequency: Максимальная частота для редких слов
            
        Returns:
            Список кортежей (слово, частота)
        """
        return self.get_words_by_frequency_range(min_freq=1, max_freq=max_frequency)
    
    def get_common_words(self, min_frequency: int = 10) -> List[Tuple[str, int]]:
        """
        Возвращает часто встречающиеся слова.
        
        Args:
            min_frequency: Минимальная частота для частых слов
            
        Returns:
            Список кортежей (слово, частота)
        """
        return self.get_words_by_frequency_range(min_freq=min_frequency)
    
    def merge_frequencies(self, other_analyzer: 'FrequencyAnalyzer') -> None:
        """
        Объединяет статистику с другим анализатором.
        
        Args:
            other_analyzer: Другой анализатор для объединения
        """
        if not other_analyzer:
            return
        
        # Объединяем частотности
        self._word_frequencies.update(other_analyzer._word_frequencies)
        
        # Объединяем статистику документов
        self._total_words += other_analyzer._total_words
        self._total_documents += other_analyzer._total_documents
        
        # Помечаем кэш как устаревший
        self._cache_dirty = True
    
    def export_frequencies_to_dict(self) -> Dict[str, int]:
        """
        Экспортирует частотности в обычный словарь.
        
        Returns:
            Словарь с частотностями
        """
        return dict(self._word_frequencies)
    
    def get_frequency_distribution(self) -> Dict[int, int]:
        """
        Возвращает распределение слов по частоте.
        
        Returns:
            Словарь {частота: количество слов}
        """
        if not self._word_frequencies:
            return {}
        
        distribution = defaultdict(int)
        for freq in self._word_frequencies.values():
            distribution[freq] += 1
        
        return dict(distribution)
    
    def get_top_words_by_percentage(self, percentage: float = 20.0) -> List[Tuple[str, int]]:
        """
        Возвращает топ слов по проценту от общего количества.
        
        Args:
            percentage: Процент слов для возврата (0-100)
            
        Returns:
            Список кортежей (слово, частота)
        """
        if not self._word_frequencies or percentage <= 0:
            return []
        
        # Вычисляем количество слов для возврата
        total_unique = len(self._word_frequencies)
        words_to_return = max(1, int(total_unique * percentage / 100))
        
        return self.get_most_frequent(words_to_return)
