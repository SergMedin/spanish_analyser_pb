"""
Централизованный менеджер spaCy для проекта.

Обеспечивает единообразную загрузку модели, оптимизацию пайплайна
и централизованную коррекцию POS согласно правилу spacy-pipeline.mdc.
"""

import spacy
import time
import logging
from typing import Optional, List, Dict, Any
from ..config import config

logger = logging.getLogger(__name__)

class SpacyManager:
    """
    Централизованный менеджер spaCy для всего проекта.
    
    Обеспечивает:
    - Единую загрузку модели с оптимизацией
    - Коррекцию систематических ошибок POS
    - Единообразную обработку текста
    """
    
    _instance: Optional['SpacyManager'] = None
    _nlp: Optional[spacy.Language] = None
    
    def __new__(cls) -> 'SpacyManager':
        """Синглтон для избежания множественной загрузки модели."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Инициализация менеджера (вызывается только один раз)."""
        if self._nlp is None:
            self._load_model()
    
    def _load_model(self) -> None:
        """Загружает модель spaCy с оптимизацией согласно правилу."""
        model_name = config.get_spacy_model()
        
        # Предупреждение о тяжёлых моделях согласно правилам UI
        if 'trf' in model_name:
            print("⚠️  Используется тяжёлая модель spaCy (transformer)")
            print("💡 Для быстрой работы рассмотрите es_core_news_md в config.yaml")
        
        try:
            # Оптимизация пайплайна: исключаем NER (согласно правилу spacy-pipeline)
            exclude_components = ['ner']  # NER не нужен для частотного анализа
            
            self._nlp = spacy.load(model_name, exclude=exclude_components)
            
            # Регистрируем кастомный атрибут для скорректированного POS
            if not spacy.tokens.Token.has_extension("corrected_pos"):
                spacy.tokens.Token.set_extension("corrected_pos", default=None)
            
            performance_note = " (медленная, но точная)" if 'trf' in model_name else " (быстрая)"
            print(f"✅ SpaCy модель {model_name} загружена{performance_note} (исключены: {exclude_components})")
            
        except Exception as e:
            raise RuntimeError(
                f"Не удалось загрузить модель spaCy '{model_name}'. "
                f"Установите модель: python -m spacy download {model_name}"
            ) from e
    
    def get_nlp(self) -> spacy.Language:
        """Возвращает загруженную модель spaCy."""
        if self._nlp is None:
            self._load_model()
        return self._nlp
    
    def analyze_text_with_corrections(self, text: str) -> spacy.tokens.Doc:
        """
        Анализирует текст с применением коррекций POS согласно правилу.
        
        Args:
            text: Текст для анализа
            
        Returns:
            spaCy Doc с скорректированными POS-тегами (через мета-данные)
        """
        t0 = time.time()
        nlp = self.get_nlp()
        # Лёгкий прогресс-лог: длина текста и модель
        logger.debug(f"spaCy анализ: старт (len={len(text)} символов, model={config.get_spacy_model()}, pipeline={nlp.pipe_names})")
        doc = nlp(text)
        
        # Применяем коррекции POS и сохраняем в кастомных атрибутах
        for token in doc:
            corrected_pos = self._correct_pos_tag(token, doc)
            # Сохраняем скорректированный POS в кастомном атрибуте
            # так как прямое изменение token.pos_ не работает надёжно
            token._.corrected_pos = corrected_pos
        dt = time.time() - t0
        logger.debug(f"spaCy анализ: завершён (tokens={len(doc)}, time={dt:.2f}s)")
        
        return doc
    
    def _correct_pos_tag(self, token: spacy.tokens.Token, doc: spacy.tokens.Doc) -> str:
        """
        Корректирует POS-тег согласно правилам spacy-pipeline.mdc.
        
        Args:
            token: Токен для коррекции
            doc: Документ для контекста
            
        Returns:
            Скорректированный POS-тег
        """
        pos_tag = token.pos_
        
        # 1. PROPN коррекция: ВСЕ PROPN → NOUN (будет обработано в консолидации)
        if pos_tag == 'PROPN':
            return 'NOUN'  # Ремап PROPN → NOUN для дальнейшей консолидации
        
        # 2. SYM фильтрация (возвращаем None для исключения)
        if pos_tag == 'SYM' and token.is_alpha and len(token.text) > 2:
            # Ошибка разметки - должно быть исключено на уровне фильтрации
            return 'X'  # Помечаем для исключения
        
        return pos_tag
    
    def _is_proper_noun(self, text: str) -> bool:
        """
        Определяет, является ли слово собственным именем.
        
        Args:
            text: Текст для проверки
            
        Returns:
            True если это собственное имя
        """
        word_lower = text.lower()
        
        # Маркеры собственных имён
        proper_noun_indicators = [
            # Географические названия
            lambda w: w in ['españa', 'madrid', 'barcelona', 'valencia', 'sevilla', 'andalucía'],
            # Имена людей (простая эвристика)
            lambda w: len(w) <= 8 and any(w.endswith(suffix) for suffix in ['o', 'a', 'ez', 'es']) and w.istitle(),
            # Организации и бренды
            lambda w: w in ['google', 'microsoft', 'toyota', 'samsung', 'apple', 'amazon'],
            # Месяцы и дни недели
            lambda w: w in ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                          'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
                          'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        ]
        
        for indicator in proper_noun_indicators:
            try:
                if indicator(word_lower):
                    return True
            except:
                continue
        
        return False
    
    def get_quality_statistics(self, doc: spacy.tokens.Doc) -> Dict[str, Any]:
        """
        Возвращает статистику качества анализа согласно правилу.
        
        Args:
            doc: Анализированный документ
            
        Returns:
            Словарь со статистикой качества
        """
        total_tokens = len([t for t in doc if t.is_alpha])
        x_sym_tokens = len([t for t in doc if t.is_alpha and t.pos_ in ['X', 'SYM']])
        
        # Статистика по частям речи
        pos_distribution = {}
        for token in doc:
            if token.is_alpha:
                pos = token.pos_
                pos_distribution[pos] = pos_distribution.get(pos, 0) + 1
        
        # Основные части речи
        main_pos_count = sum(pos_distribution.get(pos, 0) for pos in ['NOUN', 'VERB', 'ADJ'])
        main_pos_ratio = main_pos_count / total_tokens if total_tokens > 0 else 0
        
        return {
            'total_alpha_tokens': total_tokens,
            'x_sym_tokens': x_sym_tokens,
            'x_sym_ratio': x_sym_tokens / total_tokens if total_tokens > 0 else 0,
            'main_pos_ratio': main_pos_ratio,
            'pos_distribution': pos_distribution,
            'quality_warnings': self._get_quality_warnings(total_tokens, x_sym_tokens, main_pos_ratio)
        }
    
    def _get_quality_warnings(self, total_tokens: int, x_sym_tokens: int, main_pos_ratio: float) -> List[str]:
        """Генерирует предупреждения о качестве согласно правилу."""
        warnings = []
        
        if total_tokens > 0:
            x_sym_ratio = x_sym_tokens / total_tokens
            
            if x_sym_ratio > 0.15:
                warnings.append(f"⚠️ Критично: {x_sym_ratio:.1%} токенов получили X/SYM - серьёзные проблемы с текстом")
            elif x_sym_ratio > 0.10:
                warnings.append(f"⚠️ Предупреждение: {x_sym_ratio:.1%} токенов получили X/SYM - возможны проблемы с текстом")
            
            if main_pos_ratio < 0.60:
                warnings.append(f"⚠️ Низкая доля основных POS: {main_pos_ratio:.1%} (ожидается > 60%)")
        
        return warnings
    
    def reload_model(self) -> bool:
        """
        Перезагружает модель spaCy.
        
        Returns:
            True если перезагрузка успешна
        """
        try:
            self._nlp = None
            self._load_model()
            return True
        except Exception:
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Возвращает информацию о загруженной модели."""
        if self._nlp is None:
            return {'loaded': False}
        
        return {
            'name': config.get_spacy_model(),
            'loaded': True,
            'lang': self._nlp.lang,
            'pipeline': self._nlp.pipe_names,
            'excluded_components': ['ner']  # Согласно оптимизации
        }
