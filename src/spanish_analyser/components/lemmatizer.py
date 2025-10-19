"""
Компонент для лемматизации испанских слов.

Отвечает за приведение слов к базовой форме с использованием spaCy.
"""

import spacy
from typing import List, Dict, Optional
from ..interfaces.text_processor import LemmaProcessorInterface
from ..config import config
from ..cache import cached_to_file
from ..models.base_model import BaseTextModel
import logging

logger = logging.getLogger(__name__)


class LemmaProcessor(LemmaProcessorInterface):
    """Процессор для лемматизации испанских слов."""
    
    def __init__(self, model_name: str = "es_core_news_md", use_cache: bool = True, text_model: Optional[BaseTextModel] = None):
        """
        Инициализирует процессор лемматизации.
        
        Args:
            model_name: Название модели spaCy для испанского языка
            use_cache: Использовать ли кэш для лемматизации
        """
        self.model_name = model_name
        self.use_cache = use_cache
        self._cache: Dict[str, str] = {}
        self._nlp: Optional[spacy.Language] = None
        self._text_model: Optional[BaseTextModel] = text_model
        
        # Загружаем spaCy только если не передана унифицированная модель
        if self._text_model is None:
            self._load_model()
    
    def _load_model(self) -> None:
        """Получает модель spaCy через SpacyManager (без дублирования загрузки)."""
        try:
            from .spacy_manager import SpacyManager
            self._nlp = SpacyManager().get_nlp()
        except Exception as e:
            raise RuntimeError(
                f"Не удалось инициализировать spaCy через SpacyManager: {e}"
            ) from e
    
    @cached_to_file(key_prefix="spacy_lemma")
    def lemmatize(self, word: str) -> str:
        """
        Приводит слово к базовой форме.
        
        Args:
            word: Исходное слово
            
        Returns:
            Лемма слова
        """
        if not word:
            return word
        
        # Проверяем кэш
        if self.use_cache and word in self._cache:
            return self._cache[word]
        
        # Пытаемся через унифицированную модель
        if self._text_model is not None:
            try:
                result = self._text_model.analyze_text(word)
                lemma = result.tokens[0].lemma if result.tokens else word
                if self.use_cache:
                    self._cache[word] = lemma
                return lemma
            except Exception as e:
                logger.debug(f"Ошибка лемматизации через text_model: {e}")

        if not self._nlp:
            raise RuntimeError("Лемматизация недоступна: модель spaCy не загружена")

        try:
            # Обрабатываем слово через spaCy
            doc = self._nlp(word)
            if doc:
                token = doc[0]
                lemma = token.lemma_.lower()
                # Коррекция возвратных форм: spaCy может вернуть "detener él" для "detenerse"
                if token.pos_ in ['VERB', 'AUX'] and lemma.endswith(' él'):
                    original_text = token.text.lower()
                    if original_text.endswith('se'):
                        lemma = original_text
                    else:
                        lemma = lemma.replace(' él', '')
                # Сохраняем в кэш
                if self.use_cache:
                    self._cache[word] = lemma
                return lemma
        except Exception as e:
            raise RuntimeError(f"Ошибка лемматизации слова '{word}': {e}")
    
    @cached_to_file(key_prefix="spacy_lemma_batch")
    def lemmatize_batch(self, words: List[str]) -> List[str]:
        """
        Приводит список слов к базовым формам.
        
        Args:
            words: Список слов для лемматизации
            
        Returns:
            Список лемм
        """
        if not words:
            return words
        
        # Пытаемся через унифицированную модель
        if self._text_model is not None:
            try:
                result = self._text_model.analyze_text(" ".join(words))
                lemmas = [t.lemma for t in result.tokens]
                # Обновляем кэш
                if self.use_cache:
                    for w, lemma in zip(words, lemmas):
                        self._cache[w] = lemma
                return lemmas[:len(words)]
            except Exception as e:
                logger.debug(f"Ошибка батчевой лемматизации через text_model: {e}")

        if not self._nlp:
            raise RuntimeError("Лемматизация недоступна: модель spaCy не загружена")

        try:
            # Обрабатываем весь список через spaCy
            doc = self._nlp(" ".join(words))
            lemmas: List[str] = []
            word_iter_idx = 0
            for token in doc:
                if not token.text.strip():
                    continue
                lemma = token.lemma_.lower()
                if token.pos_ in ['VERB', 'AUX'] and lemma.endswith(' él'):
                    original_text = token.text.lower()
                    if original_text.endswith('se'):
                        lemma = original_text
                    else:
                        lemma = lemma.replace(' él', '')
                lemmas.append(lemma)
                word_iter_idx += 1
                if word_iter_idx >= len(words):
                    break
            # Обновляем кэш
            if self.use_cache:
                for word, lemma in zip(words, lemmas):
                    self._cache[word] = lemma
            return lemmas
        except Exception as e:
            raise RuntimeError(f"Ошибка батчевой лемматизации: {e}")
    
    def get_word_analysis(self, word: str) -> Dict[str, str]:
        """
        Возвращает детальный анализ слова.
        
        Args:
            word: Слово для анализа
            
        Returns:
            Словарь с информацией о слове
        """
        if not word:
            raise ValueError("Пустое слово для анализа")
        if not self._nlp:
            raise RuntimeError("Анализ слова недоступен: модель spaCy не загружена")
        
        try:
            doc = self._nlp(word)
            if doc:
                token = doc[0]
                return {
                    'word': word,
                    'lemma': token.lemma_,
                    'pos': token.pos_,
                    'pos_ru': self._get_pos_ru(token.pos_),
                    'tag': token.tag_,
                    'dep': token.dep_,
                    'is_alpha': token.is_alpha,
                    'is_stop': token.is_stop
                }
        except Exception as e:
            raise RuntimeError(f"Ошибка анализа слова '{word}': {e}")
    
    def _get_pos_ru(self, pos: str) -> str:
        """
        Переводит POS-тег на русский язык.
        
        УДАЛЕНО: используем единый источник из POSTagger.get_pos_tag_ru
        
        Args:
            pos: POS-тег spaCy
            
        Returns:
            Русский перевод POS-тега
        """
        # УДАЛЕНО дублирование: используем единый источник
        from .pos_tagger import POSTagger
        pos_tagger = POSTagger()
        return pos_tagger.get_pos_tag_ru(pos)
    
    def clear_cache(self) -> None:
        """Очищает кэш лемматизации."""
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Возвращает статистику кэша.
        
        Returns:
            Словарь со статистикой кэша
        """
        return {
            'cache_size': len(self._cache),
            'model_loaded': self._nlp is not None or self._text_model is not None,
            'model_name': self.model_name
        }
    
    def reload_model(self) -> bool:
        """
        Перезагружает модель spaCy.
        
        Returns:
            True если модель успешно перезагружена
        """
        try:
            from .spacy_manager import SpacyManager
            self._nlp = SpacyManager().get_nlp()
            return True
        except Exception as e:
            raise RuntimeError(f"Ошибка перезагрузки модели: {e}")
