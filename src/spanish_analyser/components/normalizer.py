"""
Компонент для нормализации испанских слов.

Принципы:
- Используем spaCy (через SpacyManager) для получения леммы и токенизации
- Избегаем ручных эвристик и «велосипедов»
- Лёгкое кэширование результатов
"""

from typing import List, Dict, Optional
from ..interfaces.text_processor import WordNormalizerInterface
from .spacy_manager import SpacyManager
import logging
import unicodedata

logger = logging.getLogger(__name__)


class WordNormalizer(WordNormalizerInterface):
    """Нормализатор для испанских слов."""
    
    def __init__(self, use_cache: bool = True):
        """
        Инициализирует нормализатор.
        
        Args:
            use_cache: Использовать ли кэш для нормализации
        """
        self.use_cache = use_cache
        self._cache: Dict[str, str] = {}
        self._nlp = None
    
    def normalize(self, word: str) -> str:
        """
        Нормализует слово для сравнения.
        
        Args:
            word: Исходное слово
            
        Returns:
            Нормализованное слово
        """
        if not word:
            return ""
        
        # Проверяем кэш
        if self.use_cache and word in self._cache:
            return self._cache[word]
        
        # Нормализуем слово через spaCy: берём лемму первого алфавитного токена
        normalized = self._normalize_with_spacy(word)
        
        # Сохраняем в кэш
        if self.use_cache:
            self._cache[word] = normalized
        
        return normalized
    
    def normalize_batch(self, words: List[str]) -> List[str]:
        """
        Нормализует список слов.
        
        Args:
            words: Список слов для нормализации
            
        Returns:
            Список нормализованных слов
        """
        if not words:
            return []
        
        return [self.normalize(word) for word in words]
    
    def _normalize_with_spacy(self, word: str) -> str:
        """Нормализация через spaCy: лемма первого алфавитного токена, с учётом возвратных форм, затем lower()."""
        text = (word or "").strip()
        # Единая Unicode-нормализация (NFC) для устойчивых сравнений и кэша
        text = unicodedata.normalize('NFC', text)
        if not text:
            return ""
        
        try:
            if self._nlp is None:
                self._nlp = SpacyManager().get_nlp()
            doc = self._nlp(text)
            
            # Ищем первый токен, содержащий буквы (spaCy может пометить как не-алфавитные сложные токены)
            for token in doc:
                raw = token.text.strip()
                if not raw:
                    continue
                has_alpha = any(ch.isalpha() for ch in raw)
                if has_alpha:
                    lemma = token.lemma_.lower()
                    # Коррекция возвратных форм: spaCy иногда даёт "detener él" для "detenerse"
                    if token.pos_ in ['VERB', 'AUX'] and lemma.endswith(' él'):
                        original_text = token.text.lower()
                        if original_text.endswith('se'):
                            return original_text
                        lemma = lemma.replace(' él', '')
                    return lemma
            
            # Если нет токенов с буквами — вернём нижний регистр сырца
            return text.lower()
            
        except Exception as e:
            logger.debug(f"spaCy-нормализация недоступна, fallback: {e}")
            return text.lower()
    
    def clear_cache(self) -> None:
        """Очищает кэш нормализации."""
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Возвращает статистику кэша.
        
        Returns:
            Словарь со статистикой кэша
        """
        return {
            'cache_size': len(self._cache),
            'cache_hits': getattr(self, '_cache_hits', 0),
            'cache_misses': getattr(self, '_cache_misses', 0)
        }
    
    def is_spanish_word(self, word: str) -> bool:
        """
        Проверяет, является ли слово испанским.
        
        Args:
            word: Слово для проверки
            
        Returns:
            True если слово содержит испанские символы
        """
        if not word:
            return False
        
        # Проверяем наличие испанских символов
        spanish_chars = set('áéíóúñüÁÉÍÓÚÑÜ')
        return any(char in spanish_chars for char in word)
    
    def get_spanish_character_count(self, word: str) -> int:
        """
        Подсчитывает количество испанских символов в слове.
        
        Args:
            word: Слово для анализа
            
        Returns:
            Количество испанских символов
        """
        if not word:
            return 0
        
        spanish_chars = set('áéíóúñüÁÉÍÓÚÑÜ')
        return sum(1 for char in word if char in spanish_chars)
