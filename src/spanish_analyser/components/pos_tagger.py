"""
Компонент для определения частей речи испанских слов.

Отвечает за определение POS-тегов, перевод на русский язык
и расчёт приоритета изучения для каждой части речи.
"""

import spacy
from typing import List, Dict, Optional, Tuple
from ..interfaces.text_processor import POSTaggerInterface
from ..cache import cached_to_file
from ..models.base_model import BaseTextModel
import logging
from .spacy_manager import SpacyManager

logger = logging.getLogger(__name__)


class POSTagger(POSTaggerInterface):
    """Теггер частей речи для испанского языка."""
    
    def __init__(self, model_name: str = "es_core_news_md", text_model: Optional[BaseTextModel] = None):
        """
        Инициализирует теггер частей речи.
        
        Args:
            model_name: Название модели spaCy для испанского языка
        """
        self.model_name = model_name
        self._nlp: Optional[spacy.Language] = None
        self._text_model: Optional[BaseTextModel] = text_model
        
        # Приоритеты изучения частей речи (чем выше, тем важнее)
        self.learning_priorities = {
            'NOUN': 10,      # Существительные - самые важные
            'VERB': 9,       # Глаголы - очень важны
            'ADJ': 8,        # Прилагательные - важны
            'ADV': 7,        # Наречия - полезны
            'PRON': 6,       # Местоимения - базовые
            'DET': 5,        # Определители - нужны
            'ADP': 4,        # Предлоги - важны для грамматики
            'NUM': 3,        # Числительные - полезны
            'CONJ': 2,       # Союзы - базовые
            'INTJ': 1,       # Междометия - не очень важны
            'PUNCT': 0,      # Знаки препинания - не изучаем
            'SYM': 0,        # Символы - не изучаем
            'X': 0,          # Другое - не изучаем
            'SPACE': 0       # Пробелы - не изучаем
        }
        
        # Загружаем модель spaCy только если нет унифицированной text_model
        if self._text_model is None:
            self._load_model()
    
    def _load_model(self) -> None:
        """Загружает модель spaCy."""
        try:
            # Единый источник spaCy модели — через SpacyManager (без дублей загрузки)
            self._nlp = SpacyManager().get_nlp()
        except Exception as e:
            raise RuntimeError(
                f"Не удалось получить spaCy модель для POS-теггинга: {e}"
            ) from e
    
    @cached_to_file(key_prefix="spacy_pos_batch")
    def get_pos_tags(self, words: List[str]) -> List[str]:
        """
        Определяет части речи для списка слов.
        
        Args:
            words: Список слов для анализа
            
        Returns:
            Список POS-тегов
        """
        if not words:
            return ['UNKNOWN'] * 0
        
        # Пробуем через унифицированную модель
        if self._text_model is not None:
            try:
                result = self._text_model.analyze_text(" ".join(words))
                pos_tags = [t.pos for t in result.tokens]
                # Дополняем до нужной длины
                while len(pos_tags) < len(words):
                    pos_tags.append('UNKNOWN')
                return pos_tags[:len(words)]
            except Exception as e:
                logger.debug(f"Ошибка POS через text_model: {e}")

        if not self._nlp:
            raise RuntimeError("POS-теггинг недоступен: модель spaCy не загружена")

        try:
            # Обрабатываем весь текст через spaCy
            text = " ".join(words)
            doc = self._nlp(text)
            # Извлекаем POS-теги
            pos_tags = []
            word_index = 0
            for token in doc:
                if token.text.strip():
                    pos_tags.append(token.pos_)
                    word_index += 1
                    if word_index >= len(words):
                        break
            # Дополняем до нужной длины
            while len(pos_tags) < len(words):
                pos_tags.append('UNKNOWN')
            return pos_tags[:len(words)]
        except Exception as e:
            raise RuntimeError(f"Ошибка определения частей речи: {e}")

    def get_genders(self, words: List[str]) -> List[Optional[str]]:
        """
        Возвращает список родов для слов по данным spaCy.
        Значения: 'Masc', 'Fem', 'Common', 'Neut', 'Unknown' или None.
        """
        if not words:
            return []
        if self._text_model is not None:
            # Текущая унифицированная модель не возвращает морфологию; используем spaCy напрямую
            pass
        if not self._nlp:
            raise RuntimeError("Определение рода недоступно: модель spaCy не загружена")
        try:
            doc = self._nlp(" ".join(words))
            # В тестовой среде doc может быть мок-объектом без итерации
            if not hasattr(doc, "__iter__"):
                return [None] * len(words)
            genders: List[Optional[str]] = []
            word_index = 0
            for token in doc:
                if getattr(token, "text", "").strip():
                    morph = getattr(token, "morph", None)
                    g = morph.get('Gender') if morph is not None else []
                    genders.append(g[0] if g else None)
                    word_index += 1
                    if word_index >= len(words):
                        break
            while len(genders) < len(words):
                genders.append(None)
            return genders[:len(words)]
        except Exception:
            # В случае ошибок spaCy или моков — безопасное значение по умолчанию
            return [None] * len(words)
    
    def get_pos_tag_ru(self, pos_tag: str) -> str:
        """
        Переводит POS-тег на русский язык.
        
        Args:
            pos_tag: POS-тег spaCy
            
        Returns:
            Русский перевод POS-тега
        """
        pos_translations = {
            'NOUN': 'Существительное',
            'VERB': 'Глагол',
            'ADJ': 'Прилагательное',
            'ADV': 'Наречие',
            'PRON': 'Местоимение',
            'PROPN': 'Собственное имя',  # ДОБАВЛЕНО
            'DET': 'Определитель',
            'ADP': 'Предлог',
            'NUM': 'Числительное',
            'CONJ': 'Союз',
            'CCONJ': 'Сочинительный союз',  # ДОБАВЛЕНО
            'SCONJ': 'Подчинительный союз',  # ДОБАВЛЕНО
            'AUX': 'Вспомогательный глагол',  # ДОБАВЛЕНО
            'PART': 'Частица',  # ДОБАВЛЕНО
            'INTJ': 'Междометие',
            'PUNCT': 'Знак препинания',
            'SYM': 'Символ',
            'X': 'Другое',
            'SPACE': 'Пробел',
            'UNKNOWN': 'Неизвестно'
        }
        
        return pos_translations.get(pos_tag, pos_tag)
    
    def get_learning_priority(self, pos_tag: str) -> int:
        """
        Возвращает приоритет изучения для части речи.
        
        Args:
            pos_tag: POS-тег
            
        Returns:
            Приоритет изучения (чем выше, тем важнее)
        """
        return self.learning_priorities.get(pos_tag, 0)
    
    def get_pos_statistics(self, words: List[str]) -> Dict[str, int]:
        """
        Возвращает статистику по частям речи.
        
        Args:
            words: Список слов для анализа
            
        Returns:
            Словарь с количеством слов по частям речи
        """
        if not words:
            return {}
        
        pos_tags = self.get_pos_tags(words)
        pos_stats = {}
        
        for pos_tag in pos_tags:
            pos_ru = self.get_pos_tag_ru(pos_tag)
            pos_stats[pos_ru] = pos_stats.get(pos_ru, 0) + 1
        
        return pos_stats
    
    def get_words_by_pos(self, words: List[str], target_pos: str) -> List[str]:
        """
        Возвращает слова с определённой частью речи.
        
        Args:
            words: Список слов
            target_pos: Целевая часть речи
            
        Returns:
            Список слов с указанной частью речи
        """
        if not words:
            return []
        
        pos_tags = self.get_pos_tags(words)
        filtered_words = []
        
        for word, pos_tag in zip(words, pos_tags):
            if pos_tag == target_pos:
                filtered_words.append(word)
        
        return filtered_words
    
    def get_learning_recommendations(self, words: List[str], max_words: int = 20) -> List[Tuple[str, str, int]]:
        """
        Возвращает рекомендации по изучению слов.
        
        Args:
            words: Список слов
            max_words: Максимальное количество слов для рекомендации
            
        Returns:
            Список кортежей (слово, часть речи, приоритет)
        """
        if not words:
            return []
        
        pos_tags = self.get_pos_tags(words)
        word_priorities = []
        
        for word, pos_tag in zip(words, pos_tags):
            priority = self.get_learning_priority(pos_tag)
            if priority > 0:  # Исключаем неважные части речи
                word_priorities.append((word, pos_tag, priority))
        
        # Сортируем по приоритету (убывание)
        word_priorities.sort(key=lambda x: x[2], reverse=True)
        
        return word_priorities[:max_words]
    
    def is_model_loaded(self) -> bool:
        """
        Проверяет, загружена ли модель.
        
        Returns:
            True если модель загружена
        """
        return self._nlp is not None or self._text_model is not None
    
    def reload_model(self) -> bool:
        """
        Перезагружает модель spaCy.
        
        Returns:
            True если модель успешно перезагружена
        """
        try:
            self._nlp = SpacyManager().get_nlp()
            return True
        except Exception as e:
            raise RuntimeError(f"Ошибка перезагрузки модели: {e}")
