"""
Унифицированный пайплайн обработки испанского текста с сохранением контекста.

Реализует лучшие практики spaCy:
- Обработка полного контекста (не отдельных слов)
- Сохранение связи между токенами и их позициями в оригинальном тексте
- Правильное сопоставление результатов spaCy с токенизированными данными
"""

import spacy
from typing import List, Dict, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from ..config import config
from .spacy_manager import SpacyManager
import logging

logger = logging.getLogger(__name__)


class TokenInfo(NamedTuple):
    """Информация о токене с полным контекстом."""
    text: str
    lemma: str
    pos: str
    morph: Dict[str, List[str]]  # Морфологические характеристики
    start_char: int  # Позиция в оригинальном тексте
    end_char: int
    is_alpha: bool
    is_valid: bool  # Проходит ли фильтры проекта


@dataclass
class TextAnalysisContext:
    """Результат анализа текста с сохранением контекста."""
    original_text: str
    tokens: List[TokenInfo]
    sentences: List[str]  # Предложения для контекста
    processing_time_ms: float


class SpanishTextPipeline:
    """
    Унифицированный пайплайн для обработки испанского текста.
    
    Следует лучшим практикам spaCy:
    1. Обрабатывает полный текст с контекстом
    2. Сохраняет связь токенов с оригинальным текстом
    3. Применяет фильтры проекта после анализа spaCy
    """
    
    def __init__(self, model_name: Optional[str] = None, min_word_length: int = 3):
        """
        Инициализирует пайплайн.
        
        Args:
            model_name: Название модели spaCy (по умолчанию из config)
            min_word_length: Минимальная длина слова для фильтрации
        """
        self.model_name = model_name or config.get_spacy_model()
        self.min_word_length = min_word_length
        self._nlp: Optional[spacy.Language] = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Получает модель spaCy через SpacyManager (единый источник)."""
        try:
            self._nlp = SpacyManager().get_nlp()
            logger.info(f"spaCy модель загружена через SpacyManager: {self._nlp.lang} | pipe={self._nlp.pipe_names}")
        except Exception as e:
            raise RuntimeError(
                f"Не удалось инициализировать spaCy через SpacyManager: {e}"
            ) from e
    
    def analyze_text(self, text: str) -> TextAnalysisContext:
        """
        Анализирует текст с сохранением полного контекста.
        
        Args:
            text: Исходный текст
            
        Returns:
            Результат анализа с контекстной информацией
        """
        import time
        start = time.time()
        
        if not text or not text.strip():
            return TextAnalysisContext(
                original_text=text,
                tokens=[],
                sentences=[],
                processing_time_ms=0.0
            )
        
        if not self._nlp:
            raise RuntimeError("Модель spaCy не загружена")
        
        # Обрабатываем весь текст целиком (ЛУЧШАЯ ПРАКТИКА #1)
        doc = self._nlp(text)
        
        # Извлекаем предложения для контекста
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        # Создаём токены с полной контекстной информацией
        tokens = []
        for token in doc:
            # Проверяем фильтры проекта
            is_valid = (
                token.is_alpha and 
                len(token.text) >= self.min_word_length and
                not token.is_punct and
                not token.is_space
            )
            
            # Извлекаем морфологические характеристики
            morph_dict = {}
            for attr in token.morph:
                key, values = attr.split('=', 1) if '=' in attr else (attr, '')
                morph_dict[key] = values.split(',') if values else []
            
            token_info = TokenInfo(
                text=token.text.lower(),
                lemma=token.lemma_.lower(),
                pos=token.pos_,
                morph=morph_dict,
                start_char=token.idx,
                end_char=token.idx + len(token.text),
                is_alpha=token.is_alpha,
                is_valid=is_valid
            )
            tokens.append(token_info)
        
        processing_time = (time.time() - start) * 1000
        
        return TextAnalysisContext(
            original_text=text,
            tokens=tokens,
            sentences=sentences,
            processing_time_ms=processing_time
        )
    
    def get_filtered_tokens(self, context: TextAnalysisContext) -> List[TokenInfo]:
        """
        Возвращает только валидные токены (прошедшие фильтры проекта).
        
        Args:
            context: Результат анализа текста
            
        Returns:
            Список валидных токенов
        """
        return [token for token in context.tokens if token.is_valid]
    
    def get_tokens_by_pos(self, context: TextAnalysisContext, pos_tags: List[str]) -> List[TokenInfo]:
        """
        Фильтрует токены по частям речи.
        
        Args:
            context: Результат анализа текста
            pos_tags: Список POS-тегов для фильтрации
            
        Returns:
            Список токенов с указанными частями речи
        """
        return [
            token for token in context.tokens 
            if token.is_valid and token.pos in pos_tags
        ]
    
    def get_nouns_with_gender(self, context: TextAnalysisContext) -> List[Tuple[TokenInfo, Optional[str]]]:
        """
        Возвращает существительные с информацией о роде.
        
        Args:
            context: Результат анализа текста
            
        Returns:
            Список кортежей (токен, род)
        """
        nouns = self.get_tokens_by_pos(context, ['NOUN'])
        result = []
        
        for noun in nouns:
            gender = None
            if 'Gender' in noun.morph and noun.morph['Gender']:
                gender = noun.morph['Gender'][0]  # Берём первое значение
            result.append((noun, gender))
        
        return result
    
    def format_noun_with_article(self, lemma: str, gender: Optional[str]) -> str:
        """
        Форматирует существительное с артиклем по роду.
        
        Args:
            lemma: Лемма существительного
            gender: Род ('Masc', 'Fem', или None)
            
        Returns:
            Отформатированная строка с артиклем
        """
        if gender == 'Masc':
            return f"el {lemma}"
        elif gender == 'Fem':
            return f"la {lemma}"
        else:
            return lemma  # Без артикля если род неизвестен
    
    def get_context_around_token(self, context: TextAnalysisContext, token: TokenInfo, 
                                window: int = 2) -> str:
        """
        Возвращает контекст вокруг токена.
        
        Args:
            context: Результат анализа текста
            token: Токен для которого нужен контекст
            window: Количество токенов слева и справа
            
        Returns:
            Строка с контекстом
        """
        # Находим индекс токена
        try:
            token_index = context.tokens.index(token)
        except ValueError:
            return ""
        
        # Извлекаем окно вокруг токена
        start_idx = max(0, token_index - window)
        end_idx = min(len(context.tokens), token_index + window + 1)
        
        context_tokens = context.tokens[start_idx:end_idx]
        return " ".join(t.text for t in context_tokens)
    
    def reload_model(self) -> bool:
        """
        Перезагружает модель spaCy.
        
        Returns:
            True если перезагрузка успешна
        """
        try:
            self._load_model()
            return True
        except Exception:
            return False
    
    def get_model_info(self) -> Dict[str, str]:
        """Возвращает информацию о загруженной модели."""
        return {
            'name': self.model_name,
            'loaded': self._nlp is not None,
            'type': 'spacy'
        }
