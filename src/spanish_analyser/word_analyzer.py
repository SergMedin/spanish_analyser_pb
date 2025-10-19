"""
Модуль для анализа испанских слов

Предоставляет функциональность для:
- Подсчёта частоты слов
- Категоризации слов по темам
- Анализа частей речи с помощью spaCy
- Создания отчётов
"""

import json
import pandas as pd
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import spacy
from .config import config
from .components.word_comparator import WordComparator
from .components.pos_tagger import POSTagger
from .components.tokenizer import TokenProcessor
from .components.lemmatizer import LemmaProcessor
from .components.frequency_analyzer import FrequencyAnalyzer
from .components.normalizer import WordNormalizer
from .components.exporter import ResultExporter
from .interfaces.text_processor import AnalysisResult, WordInfo
import logging

logger = logging.getLogger(__name__)


class WordAnalyzer:
    """Класс для анализа испанских слов с использованием spaCy"""
    
    def __init__(self,
                 collection_path: Optional[str] = None,
                 deck_pattern: str = "Spanish*",
                 min_word_length: Optional[int] = None,
                 spacy_model: Optional[str] = None,
                 output_dir: Optional[str] = None):
        """Инициализация анализатора слов"""
        self.word_frequencies = Counter()
        self.word_categories = defaultdict(list)
        self.known_words = set()
        self.word_pos_tags = {}  # Словарь для хранения частей речи
        self.word_comparator: Optional[WordComparator] = None  # Современная интеграция с ANKI
        # Безопасное хранение токенных деталей по (lemma, pos, gender) вместо только lemma
        self.token_details = {}  # Dict[(lemma, pos, gender), TokenDetails]
        self.pos_tagger = POSTagger(model_name=config.get_spacy_model())  # Единый источник POS→RU
        # Минимальная длина слова берётся из конфигурации, чтобы централизованно
        # управлять порогом фильтрации коротких слов во всех частях приложения.
        # Это важно, т.к. при использовании spaCy мы добавляем в частоты ЛЕММУ,
        # которая может быть короче исходной формы (например, «vamos» → «ir»),
        # и именно длину леммы необходимо сравнивать с порогом.
        self.min_word_length = min_word_length or config.get_min_word_length()
        
        # Список испанских артиклей для удаления
        self.spanish_articles = {
            'el', 'la', 'los', 'las',  # Определённые артикли
            'un', 'una', 'unos', 'unas',  # Неопределённые артикли
            'este', 'esta', 'estos', 'estas',  # Указательные местоимения
            'ese', 'esa', 'esos', 'esas',
            'aquel', 'aquella', 'aquellos', 'aquellas',
            'mi', 'tu', 'su', 'nuestro', 'vuestro',  # Притяжательные местоимения
            'mi', 'mis', 'tu', 'tus', 'su', 'sus',
            'nuestro', 'nuestra', 'nuestros', 'nuestras',
            'vuestro', 'vuestra', 'vuestros', 'vuestras'
        }
        
        # Загружаем модель spaCy для испанского языка из конфигурации с оптимизацией
        spacy_model = spacy_model or config.get_spacy_model()
        # Используем централизованный менеджер spaCy (согласно рефакторингу)
        from .components.spacy_manager import SpacyManager
        self.spacy_manager = SpacyManager()
        self.nlp = self.spacy_manager.get_nlp()
        
        # Инициализируем компонентную архитектуру (поддержка нового API)
        self.tokenizer = TokenProcessor(min_length=self.min_word_length, include_numbers=False)
        self.lemmatizer = LemmaProcessor(model_name=spacy_model, use_cache=True, text_model=None)
        # pos_tagger уже инициализирован выше
        self.frequency_analyzer = FrequencyAnalyzer()
        # Инициализируем WordComparator, если ещё не инициализирован через init_anki_integration
        if self.word_comparator is None:
            try:
                # Убираем звездочку из deck_pattern для WordComparator
                clean_deck_pattern = deck_pattern.rstrip('*')
                # Не загружаем автоматически при создании — сделаем это явно в init_anki_integration()
                self.word_comparator = WordComparator(collection_path=collection_path, deck_pattern=clean_deck_pattern, autoload=False)
            except Exception:
                clean_deck_pattern = deck_pattern.rstrip('*')
                self.word_comparator = WordComparator(collection_path=collection_path, deck_pattern=clean_deck_pattern, autoload=False)
        self.word_normalizer = WordNormalizer(use_cache=True)
        self.exporter = ResultExporter(output_dir=output_dir or config.get_results_folder())
        # Для нового API ожидаются эти поля
        self.spacy_model = spacy_model
        
        # УДАЛЕНО: POS_NAMES теперь используется единый источник из POSTagger.get_pos_tag_ru

    # ===== Методы нового API (совместимость с word_analyzer_new.py) =====

    def analyze_text(self, text: str) -> AnalysisResult:
        """Анализирует текст и возвращает результат (новый API)."""
        import time as _time
        start = _time.time()
        if not text or not text.strip():
            return self._create_empty_result()

        tokens = self.tokenizer.tokenize(text)
        if not tokens:
            return self._create_empty_result()

        lemmas = self.lemmatizer.lemmatize_batch(tokens)
        pos_tags = self.pos_tagger.get_pos_tags(tokens)
        pos_tags_ru = [self.pos_tagger.get_pos_tag_ru(p) for p in pos_tags]
        try:
            genders = self.pos_tagger.get_genders(tokens)
        except Exception:
            genders = [None] * len(tokens)

        # Подсчёт частотности по правилам нового API
        counters_tokens: List[str] = []
        for lemma, pos, gender in zip(lemmas, pos_tags, genders):
            key = lemma
            if pos == 'NOUN':
                art = 'el' if gender == 'Masc' else ('la' if gender == 'Fem' else '')
                key = f"{art + ' ' if art else ''}{lemma}"
            counters_tokens.append(key)
        frequency_dict = self.frequency_analyzer.count_frequency(counters_tokens)

        words_info: List[WordInfo] = []
        for tok, lemma, pos, pos_ru, gender in zip(tokens, lemmas, pos_tags, pos_tags_ru, genders):
            if pos == 'NOUN':
                art = 'el' if gender == 'Masc' else ('la' if gender == 'Fem' else '')
                freq_key = f"{art + ' ' if art else ''}{lemma}"
            else:
                freq_key = lemma
            freq = frequency_dict.get(freq_key, 0)
            is_known = False
            try:
                if self.word_comparator:
                    if config.is_lemma_aware_known_enabled():
                        is_known = self.word_comparator.is_token_known(lemma=lemma, pos=pos, gender=gender)
                        logger.debug(f"🔍 Проверка известности LEMMA-режим: '{lemma}' (pos={pos}, gender={gender}) → {is_known}")
                    else:
                        is_known = self.word_comparator.is_word_known(tok)
                        logger.debug(f"🔍 Проверка известности ТОЧНОЕ-совпадение: '{tok}' → {is_known}")
                else:
                    logger.debug(f"⚠️ WordComparator не доступен для слова: '{tok}'")
            except Exception as e:
                logger.debug(f"❌ Ошибка проверки известности для '{tok}': {e}")
                pass
            words_info.append(WordInfo(
                word=tok,
                pos_tag=pos,
                pos_tag_ru=pos_ru,
                frequency=freq,
                lemma=lemma,
                is_known=is_known,
                context_examples=None,
                comment=None,
                gender=gender
            ))

        processing_time = _time.time() - start
        return AnalysisResult(
            words=words_info,
            frequency_dict=frequency_dict,
            unknown_words=[w.word for w in words_info if not w.is_known],
            total_words=len(tokens),
            unique_words=len(frequency_dict),
            processing_time=processing_time,
            metadata={
                'spacy_model': getattr(self, 'spacy_model', config.get_spacy_model()),
                'min_word_length': self.min_word_length,
                'collection_path': getattr(self.word_comparator, 'collection_path', ''),
                'deck_pattern': getattr(self.word_comparator, 'deck_pattern', ''),
            }
        )

    def get_unknown_words_for_learning(self, result: AnalysisResult) -> List[WordInfo]:
        if not result or not result.words:
            return []
        unknown = [w for w in result.words if not w.is_known]
        def _prio(w: WordInfo):
            return (w.frequency, self.pos_tagger.get_learning_priority(w.pos_tag))
        unknown.sort(key=_prio, reverse=True)
        return unknown

    def export_results(self, result: AnalysisResult, base_filename: str = "spanish_analysis"):
        return self.exporter.export_all_formats(result, base_filename)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            'tokenizer': self.tokenizer.get_token_statistics([]),
            'lemmatizer': self.lemmatizer.get_cache_stats(),
            'pos_tagger': {'model_loaded': True, 'model_name': self.pos_tagger.model_name},
            'frequency_analyzer': self.frequency_analyzer.get_frequency_statistics(),
            'word_comparator': (self.word_comparator.get_comparison_statistics() if self.word_comparator else {}),
            'word_normalizer': self.word_normalizer.get_cache_stats(),
            'settings': {
                'min_word_length': self.min_word_length,
                'spacy_model': getattr(self, 'spacy_model', config.get_spacy_model()),
                'output_dir': config.get_results_folder()
            }
        }

    def clear_caches(self) -> None:
        try:
            self.lemmatizer.clear_cache()
            self.word_normalizer.clear_cache()
            self.frequency_analyzer.reset_statistics()
        except Exception:
            pass

    def reload_models(self) -> bool:
        ok1 = False
        ok2 = False
        try:
            ok1 = self.lemmatizer.reload_model()
        except Exception:
            pass
        try:
            ok2 = self.pos_tagger.reload_model()
        except Exception:
            pass
        return bool(ok1 and ok2)

    def _create_empty_result(self) -> AnalysisResult:
        return AnalysisResult(words=[], frequency_dict={}, unknown_words=[], total_words=0, unique_words=0, processing_time=0.0)

    # Методы обратной совместимости нового API
    def analyze_spanish_text(self, text: str) -> Dict[str, Any]:
        res = self.analyze_text(text)
        return {
            'words': [w.word for w in res.words],
            'frequencies': res.frequency_dict,
            'unknown_words': res.unknown_words,
            'total_words': res.total_words,
            'unique_words': res.unique_words,
            'processing_time': res.processing_time,
            'pos_tags': {w.word: w.pos_tag_ru for w in res.words},
        }

    def get_word_frequency(self, word: str) -> int:
        return self.frequency_analyzer.get_word_frequency(word)

    def get_most_frequent_words(self, n: int = 10) -> List[tuple]:
        return self.frequency_analyzer.get_most_frequent(n)

    # Совместимость с тестами качества: fallback-метод
    def determine_pos(self, lemma: str) -> str:
        try:
            tag = self.pos_tagger.get_pos_tags([lemma])[0]
            return self.pos_tagger.get_pos_tag_ru(tag).lower()
        except Exception:
            return 'неизвестно'
    
    def normalize_word(self, word: str) -> str:
        """Нормализует слово для сравнения через WordNormalizer (spaCy)."""
        return self.word_normalizer.normalize(word)
    
    def is_word_known(self, word: str) -> bool:
        """
        Проверяет, известно ли слово через WordComparator или старую логику
        
        Args:
            word: Слово для проверки
            
        Returns:
            True если слово известно, False в противном случае
        """
        if not word:
            return False
        
        # Сначала проверяем локальный список известных слов (для тестов и legacy-логики)
        normalized_word = self.normalize_word(word)
        if normalized_word in self.known_words:
            return True

        # Если доступен WordComparator, используем его
        if self.word_comparator:
            if self.word_comparator.is_word_known(word):
                return True
        
        # Иначе используем старую логику для совместимости
        if not self.known_words:
            return False
        
        # Проверяем точное совпадение
        if normalized_word in self.known_words:
            return True
        
        # Проверяем совпадение с нормализованными известными словами
        # Используем предварительно вычисленные нормализованные формы
        if hasattr(self, '_normalized_known_words'):
            if normalized_word in self._normalized_known_words:
                return True
        else:
            # Создаём кэш нормализованных известных слов при первом вызове
            self._normalized_known_words = set()
            for known_word in self.known_words:
                normalized_known = self.normalize_word(known_word)
                if normalized_known:
                    self._normalized_known_words.add(normalized_known)
            
            # Теперь проверяем в кэше
            if normalized_word in self._normalized_known_words:
                return True
        
        return False
    
    # УДАЛЕНО: устаревшие методы POS-анализа
    # Теперь используется централизованный SpacyManager
    
    def init_anki_integration(self) -> bool:
        """
        Инициализирует современную интеграцию с ANKI через AnkiConnect.
        
        Returns:
            True если интеграция успешна
        """
        try:
            if self.word_comparator is None:
                # Создадим и загрузим известные слова
                self.word_comparator = WordComparator(deck_pattern="Spanish", autoload=True)
            elif self.word_comparator.get_known_words_count() == 0:
                # Отложенная загрузка, если компаратор уже создан
                try:
                    # Внутренний метод загрузки через AnkiConnect
                    self.word_comparator._load_known_words_modern()  # type: ignore[attr-defined]
                except Exception:
                    # В случае ошибок — пересоздадим с автозагрузкой
                    self.word_comparator = WordComparator(deck_pattern="Spanish", autoload=True)
            known_count = self.word_comparator.get_known_words_count()
            if known_count > 0:
                # Обновляем deprecated поле для обратной совместимости
                self.known_words = set(self.word_comparator.known_words)
                logger.info(f"Инициализирована интеграция с ANKI: {known_count} известных слов")
                return True
            else:
                logger.warning("ANKI недоступен или нет испанских колод")
                return False
        except Exception as e:
            logger.error(f"Ошибка инициализации ANKI: {e}")
            return False
    
    # УДАЛЕНО: устаревшие методы determine_pos_* заменены на SpacyManager
    
    def load_known_words_from_anki(self, anki_integration: Any, deck_pattern: str = None, field_names: List[str] = None) -> bool:
        """
        Загружает известные слова из колод Anki
        
        Args:
            anki_integration: Экземпляр AnkiIntegration
            deck_pattern: Паттерн для поиска колод (если не указан, используется из конфигурации)
            field_names: Список названий полей для извлечения слов (если не указан, используется из конфигурации)
            
        Returns:
            True если загрузка успешна, False в противном случае
        """
        # Используем значения по умолчанию из конфигурации
        deck_pattern = deck_pattern or config.get_deck_pattern()
        field_names = field_names or config.get_field_names()
        
        try:
            if not anki_integration.is_connected():
                logger.error("Нет подключения к Anki для загрузки известных слов")
                return False
            
            # Находим заметки в испанских колодах
            note_ids = anki_integration.find_notes_by_deck(deck_pattern)
            if not note_ids:
                logger.warning(f"Не найдено заметок в испанских колодах по паттерну: {deck_pattern}")
                return False
            
            logger.info(f"Найдено {len(note_ids)} заметок в испанских колодах")
            
            # Извлекаем текст из заметок
            notes_data = anki_integration.extract_text_from_notes(note_ids, field_names)
            
            # Собираем все слова из текста
            all_words = set()
            normalized_words = set()
            
            for note_data in notes_data:
                for text in note_data['texts']:
                    if text:
                        # Очищаем текст от HTML и извлекаем слова
                        from .text_processor import SpanishTextProcessor
                        processor = SpanishTextProcessor()
                        cleaned_text = processor.clean_text(text, remove_prefixes=False)
                        words = processor.extract_spanish_words(cleaned_text)
                        
                        for word in words:
                            if word.strip():
                                # Сохраняем оригинальное слово
                                all_words.add(word.strip())
                                # Сохраняем нормализованное слово
                                normalized = self.normalize_word(word)
                                if normalized:
                                    normalized_words.add(normalized)
            
            # Устанавливаем известные слова (и оригинальные, и нормализованные)
            self.known_words = all_words | normalized_words
            
            logger.info(f"Загружено {len(all_words)} оригинальных слов из Anki")
            logger.info(f"Добавлено {len(normalized_words)} нормализованных форм")
            logger.info(f"Всего уникальных известных слов: {len(self.known_words)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке известных слов из Anki: {e}")
            logger.info("Проверьте подключение к Anki и корректность паттерна колод в конфигурации")
            return False
    
    def load_known_words(self, file_path: str) -> bool:
        """
        Загружает список известных слов из файла (устаревший метод)
        
        Args:
            file_path: Путь к файлу с известными словами
            
        Returns:
            True если загрузка успешна, False в противном случае
        """
        logger.warning("Метод load_known_words() устарел. Используйте load_known_words_from_anki()")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                words = [line.strip().lower() for line in f if line.strip()]
                self.known_words = set(words)
            logger.info(f"Загружено {len(words)} известных слов из файла")
            return True
        except Exception as e:
            logger.error(f"Ошибка при загрузке известных слов: {e}")
            return False
    
    def add_words_from_text(self, text: str, weight: int = 1) -> None:
        """
        Добавляет слова из текста в статистику частот с определением частей речи
        (обновлённая версия с поддержкой артиклей для существительных)
        
        Args:
            text: Текст для анализа
            weight: Вес для подсчёта (по умолчанию 1)
        """
        if not text:
            return
        
        if not self.nlp:
            raise RuntimeError("Анализ текста невозможен: модель spaCy не загружена")
        try:
            import time as _time
            _t0 = _time.time()
            logger.debug(f"Добавление слов: анализ spaCy (len={len(text)} символов)")
            # Анализируем текст с применением коррекций (централизованная логика)
            doc = self.spacy_manager.analyze_text_with_corrections(text)
            logger.debug(f"Добавление слов: spaCy doc готов (tokens={len(doc)}, dt={_time.time()-_t0:.2f}s)")
            
            # === ЦЕНТРАЛИЗОВАННЫЕ ЭВРИСТИКИ КАЧЕСТВА ===
            quality_stats = self.spacy_manager.get_quality_statistics(doc)
            for warning in quality_stats['quality_warnings']:
                logger.warning(warning)
            
            _t1 = _time.time()
            added_tokens = 0
            for token in doc:
                if not token.is_alpha:
                    continue
                lemma = token.lemma_.lower()
                
                # === ИСПОЛЬЗУЕМ СКОРРЕКТИРОВАННЫЙ POS ===
                # Приоритет: скорректированный POS из SpacyManager, иначе оригинальный
                pos_tag = getattr(token._, 'corrected_pos', None) or token.pos_
                
                # === ФИЛЬТРАЦИЯ ПОСЛЕ КОРРЕКЦИЙ ===
                # Коррекции уже применены в SpacyManager, теперь только фильтруем
                if pos_tag == 'X' and token.is_alpha and len(token.text) > 2:
                    # Токен помечен как проблемный в SpacyManager - пропускаем
                    continue
                elif pos_tag == 'SYM':
                    # Оставшиеся SYM токены исключаем из анализа слов
                    continue
                
                # Исправляем проблему с возвратными глаголами
                # spaCy даёт лемму "detener él" для "detenerse", но нам нужно "detenerse"
                if pos_tag in ['VERB', 'AUX'] and lemma.endswith(' él'):
                    # Если исходная форма заканчивается на 'se', сохраняем её
                    original_text = token.text.lower()
                    if original_text.endswith('se'):
                        lemma = original_text
                    else:
                        # Иначе убираем ' él' из леммы
                        lemma = lemma.replace(' él', '')
                
                if len(lemma) < self.min_word_length:
                    continue
                pos_name = self.pos_tagger.get_pos_tag_ru(pos_tag)
                
                # Извлекаем морфологические характеристики (правильный способ)
                gender = None
                if token.morph:
                    # Парсим морфологические признаки
                    morph_dict = {}
                    for feature in token.morph:
                        if '=' in feature:
                            key, value = feature.split('=', 1)
                            morph_dict[key] = value.split(',')
                    if 'Gender' in morph_dict:
                        gender = morph_dict['Gender'][0]  # Берем первое значение

                # Раннее восстановление рода NOUN по ближайшему DET (el/la/los/las)
                if pos_tag == 'NOUN' and not gender:
                    try:
                        # Ищем предшествующий определитель
                        if token.i > 0:
                            det = doc[token.i - 1]
                            if det.pos_ == 'DET':
                                art = det.lemma_.lower() if det.lemma_ else det.text.lower()
                                if art in ('el', 'los'):
                                    gender = 'Masc'
                                elif art in ('la', 'las'):
                                    gender = 'Fem'
                        # В спорных случаях можно проверить и следующий токен
                        if not gender and token.i + 1 < len(doc):
                            det_next = doc[token.i + 1]
                            if det_next.pos_ == 'DET':
                                art = det_next.lemma_.lower() if det_next.lemma_ else det_next.text.lower()
                                if art in ('el', 'los'):
                                    gender = 'Masc'
                                elif art in ('la', 'las'):
                                    gender = 'Fem'
                    except Exception:
                        pass
                
                # Для существительных формируем ключ с артиклем
                if pos_tag == 'NOUN':
                    if gender == 'Masc':
                        display_word = f"el {lemma}"
                    elif gender == 'Fem':
                        display_word = f"la {lemma}"
                    else:
                        display_word = lemma  # Без артикля если род неизвестен
                    freq_key = f"{display_word} ({pos_name})"
                else:
                    # Для остальных частей речи используем лемму как есть
                    freq_key = f"{lemma} ({pos_name})"
                
                self.word_frequencies[freq_key] += weight
                self.word_pos_tags[lemma] = pos_name.lower()
                
                # Безопасное хранение токенных деталей по (lemma, pos, gender)
                safe_key = (lemma, pos_tag, gender)
                self.token_details[safe_key] = {
                    'pos': pos_tag,
                    'pos_ru': pos_name,
                    'gender': gender,
                    'original_text': token.text,
                    'display_form': display_word if pos_tag == 'NOUN' else lemma,
                    'freq_key': freq_key  # Ключ для частотности
                }
                added_tokens += 1
                
            logger.debug(f"Добавление слов: постобработка завершена (added={added_tokens}, dt={_time.time()-_t1:.2f}s)")
        except Exception as e:
            raise RuntimeError(f"Ошибка при анализе текста с spaCy: {e}")
    
    def _add_words_basic(self, text: str, weight: int = 1) -> None:
        raise RuntimeError("Базовая обработка без spaCy отключена политикой No Fallback")
    
    def categorize_words_by_frequency(self, min_frequency: int = 1) -> Dict[str, List[str]]:
        """
        Категоризует слова по частоте использования
        
        Args:
            min_frequency: Минимальная частота для включения в категорию
            
        Returns:
            Словарь с категориями и списками слов
        """
        categories = {
            'очень_часто': [],      # > 100 раз
            'часто': [],            # 50-100 раз
            'средне': [],           # 20-49 раз
            'редко': [],            # 5-19 раз
            'очень_редко': []       # 1-4 раза
        }
        
        for word_with_pos, freq in self.word_frequencies.most_common():
            if freq < min_frequency:
                continue
                
            if freq > 100:
                categories['очень_часто'].append(word_with_pos)
            elif freq > 50:
                categories['часто'].append(word_with_pos)
            elif freq > 20:
                categories['средне'].append(word_with_pos)
            elif freq > 5:
                categories['редко'].append(word_with_pos)
            else:
                categories['очень_редко'].append(word_with_pos)
        
        return categories
    
    def get_new_words(self, exclude_known: bool = True) -> List[str]:
        """
        Получает список новых (неизвестных) слов
        
        Args:
            exclude_known: Исключать ли известные слова
            
        Returns:
            Список новых слов, отсортированный по частоте
        """
        if exclude_known:
            new_words = []
            for word_with_pos, freq in self.word_frequencies.most_common():
                # Извлекаем только слово без части речи
                if ' (' in word_with_pos and word_with_pos.endswith(')'):
                    word = word_with_pos.split(' (')[0]
                else:
                    word = word_with_pos
                
                # Используем улучшенную проверку на известность
                if not self.is_word_known(word):
                    new_words.append(word_with_pos)
        else:
            new_words = [word_with_pos for word_with_pos, freq in self.word_frequencies.most_common()]
        
        return new_words
    
    def get_top_words(self, n: int = 50, exclude_known: bool = True) -> List[Tuple[str, int]]:
        """
        Получает топ N слов по частоте
        
        Args:
            n: Количество слов для возврата
            exclude_known: Исключать ли известные слова
            
        Returns:
            Список кортежей (слово, частота)
        """
        if exclude_known:
            top_words = []
            for word_with_pos, freq in self.word_frequencies.most_common():
                # Извлекаем только слово без части речи
                if ' (' in word_with_pos and word_with_pos.endswith(')'):
                    word = word_with_pos.split(' (')[0]
                else:
                    word = word_with_pos
                
                # Используем улучшенную проверку на известность
                if not self.is_word_known(word):
                    top_words.append((word_with_pos, freq))
        else:
            top_words = [(word_with_pos, freq) for word_with_pos, freq in self.word_frequencies.most_common()]
        
        return top_words[:n]
    
    def export_to_excel(self, file_path: str, include_categories: bool = True) -> None:
        """
        Экспортирует статистику слов в Excel файл с артиклями для существительных и комментариями ANKI
        
        Args:
            file_path: Путь для сохранения Excel файла
            include_categories: Параметр оставлен для совместимости, но не используется
        """
        try:
            import time as _time
            _t0 = _time.time()
            # Вычисляем общее количество всех слов (включая повторения)
            total_words = sum(self.word_frequencies.values())
            logger.debug(f"Экспорт в Excel: старт (total_words={total_words}, unique={len(self.word_frequencies)})")
            
            # Получаем настройки из конфигурации
            decimal_places = config.get_frequency_decimal_places()
            sheet_name = config.get_main_sheet_name()
            
            # === УМНАЯ КОНСОЛИДАЦИЯ ПО ЛЕММАМ (профессиональная версия) ===
            # Используем данные из token_details, который уже содержит правильные лемматизированные данные spaCy
            lemma_pos_analysis = {}  # lemma -> {pos_ru: {freq_key: freq, total_count: int}}
            
            # Группируем по РЕАЛЬНЫМ леммам из spaCy (из token_details)
            for safe_key, details in self.token_details.items():
                lemma, pos_tag, gender = safe_key
                freq_key = details['freq_key']
                pos_ru = details['pos_ru']
                
                # Получаем частоту из word_frequencies
                freq = self.word_frequencies.get(freq_key, 0)
                if freq == 0:
                    continue
                
                if lemma not in lemma_pos_analysis:
                    lemma_pos_analysis[lemma] = {}
                
                if pos_ru not in lemma_pos_analysis[lemma]:
                    lemma_pos_analysis[lemma][pos_ru] = {'entries': {}, 'total_count': 0}
                
                lemma_pos_analysis[lemma][pos_ru]['entries'][freq_key] = freq
                lemma_pos_analysis[lemma][pos_ru]['total_count'] += freq
            
            # Шаг 1: применяем умную консолидацию
            # Мелкие типы речи, которые добавляем к доминирующему существительному
            minor_pos_types = {'Собственное имя', 'Междометие', 'Числительное', 'Знак препинания', 'Символ', 'Частица', 'Другое'}
            
            smart_consolidated = {}
            
            _t_idx = _time.time()
            for base_lemma, pos_data in lemma_pos_analysis.items():
                # Общий счётчик слов для леммы (именно count, а не POS)
                total_lemma_count = sum(data['total_count'] for data in pos_data.values())
                
                # Ищем доминирующее существительное с родом (>33%)
                dominant_noun_key = None
                dominant_noun_count = 0
                target_noun_found = False
                
                if 'Существительное' in pos_data:
                    noun_count = pos_data['Существительное']['total_count']
                    if noun_count / total_lemma_count > 0.33:  # > 33% от всех слов леммы
                        # Ищем самое частотное существительное С УКАЗАННЫМ РОДОМ
                        # Используем реальные данные из token_details для определения рода
                        noun_entries = pos_data['Существительное']['entries']
                        
                        nouns_with_gender = {}
                        nouns_without_gender = {}
                        
                        for freq_key, count in noun_entries.items():
                            # Находим соответствующую запись в token_details для получения gender
                            gender = None
                            for safe_key, details in self.token_details.items():
                                if details['freq_key'] == freq_key:
                                    gender = safe_key[2]  # gender из (lemma, pos, gender)
                                    break
                            
                            if gender in ['Masc', 'Fem']:
                                nouns_with_gender[freq_key] = count
                            else:
                                nouns_without_gender[freq_key] = count
                        
                        # Выбираем самое частотное существительное С РОДОМ (приоритет)
                        if nouns_with_gender:
                            dominant_noun_key = max(nouns_with_gender.keys(), key=lambda k: nouns_with_gender[k])
                            dominant_noun_count = noun_count
                            target_noun_found = True
                        # Если нет существительных с родом, но есть существительные без рода
                        elif nouns_without_gender:
                            dominant_noun_key = max(nouns_without_gender.keys(), key=lambda k: nouns_without_gender[k])
                            dominant_noun_count = noun_count
                            target_noun_found = True
                            # Обнуляем nouns_with_gender, так как консолидируем с существительным без рода
                            nouns_with_gender = {}
                
                if target_noun_found:
                    # Консолидируем: добавляем мелкие POS к целевому существительному
                    
                    # Определяем начальный count целевого существительного
                    if nouns_with_gender and dominant_noun_key in nouns_with_gender:
                        # Консолидируем с существительным С РОДОМ
                        consolidated_count = nouns_with_gender[dominant_noun_key]
                        consolidating_with_gender = True
                    else:
                        # Консолидируем с существительным БЕЗ РОДА
                        consolidated_count = nouns_without_gender[dominant_noun_key]
                        consolidating_with_gender = False
                    
                    minor_count = 0
                    
                    # 1. Добавляем мелкие POS
                    for pos_ru, data in pos_data.items():
                        if pos_ru in minor_pos_types:
                            minor_count += data['total_count']
                            consolidated_count += data['total_count']
                    
                    # 2. Добавляем существительные противоположного типа (с родом к без рода или наоборот)
                    if consolidating_with_gender:
                        # Консолидируем С РОДОМ: добавляем существительные БЕЗ РОДА
                        for freq_key, count in nouns_without_gender.items():
                            minor_count += count
                            consolidated_count += count
                    else:
                        # Консолидируем БЕЗ РОДА: добавляем существительные С РОДОМ (если есть)
                        for freq_key, count in nouns_with_gender.items():
                            minor_count += count
                            consolidated_count += count
                    
                    # Отладочный вывод для проверки
                    # if minor_count > 0:
                    #     target_type = "с родом" if consolidating_with_gender else "без рода"
                    #     initial_count = nouns_with_gender[dominant_noun_key] if consolidating_with_gender else nouns_without_gender[dominant_noun_key]
                    #     print(f"🧠 Консолидация леммы '{lemma}' ({target_type}): {initial_count} + {minor_count} = {consolidated_count}")
                    
                    # Сохраняем консолидированный результат
                    smart_consolidated[dominant_noun_key] = consolidated_count
                    
                    # Добавляем остальные существительные (кроме целевого и уже добавленных)
                    if consolidating_with_gender:
                        # Добавляем остальные существительные С РОДОМ (кроме целевого)
                        for freq_key, count in nouns_with_gender.items():
                            if freq_key != dominant_noun_key:
                                smart_consolidated[freq_key] = count
                        # nouns_without_gender уже добавлены к целевому
                    else:
                        # Добавляем остальные существительные БЕЗ РОДА (кроме целевого)
                        for freq_key, count in nouns_without_gender.items():
                            if freq_key != dominant_noun_key:
                                smart_consolidated[freq_key] = count
                        # nouns_with_gender уже добавлены к целевому
                    
                    # Добавляем остальные POS (не мелкие и не существительные)
                    for pos_ru, data in pos_data.items():
                        if pos_ru not in minor_pos_types and pos_ru != 'Существительное':
                            for freq_key, freq in data['entries'].items():
                                smart_consolidated[freq_key] = freq
                else:
                    # Нет доминирующего существительного с родом - оставляем как есть
                    for pos_ru, data in pos_data.items():
                        for freq_key, freq in data['entries'].items():
                            smart_consolidated[freq_key] = freq
            logger.debug(f"Экспорт в Excel: индексация лемм завершена (dt={_time.time()-_t0:.2f}s)")
            
            # === КОНСОЛИДАЦИЯ ВАРИАНТОВ СУЩЕСТВИТЕЛЬНЫХ (профессиональная версия) ===
            # Используем реальные данные из token_details для группировки по лемме + определению gender
            lemma_variants = {}  # lemma -> {'with_gender': {freq_key: freq}, 'without_gender': {freq_key: freq}}
            non_nouns = {}  # Не-существительные как есть
            
            for freq_key, freq in smart_consolidated.items():
                # Находим соответствующую запись в token_details
                details = None
                for safe_key, d in self.token_details.items():
                    if d['freq_key'] == freq_key:
                        details = d
                        lemma, pos_tag, gender = safe_key
                        break
                
                if details is None:
                    # Запись не найдена - добавляем как есть (может быть артефакт)
                    non_nouns[freq_key] = freq
                    continue
                
                pos_ru = details['pos_ru']
                
                if pos_ru == 'Существительное':
                    # Группируем варианты существительных по реальной лемме из spaCy
                    if lemma not in lemma_variants:
                        lemma_variants[lemma] = {'with_gender': {}, 'without_gender': {}}
                    
                    if gender in ['Masc', 'Fem']:
                        lemma_variants[lemma]['with_gender'][freq_key] = freq
                    else:
                        lemma_variants[lemma]['without_gender'][freq_key] = freq
                else:
                    # Не-существительные сохраняем как есть
                    non_nouns[freq_key] = freq
            
            # Шаг 2: консолидируем варианты существительных (на основе РЕАЛЬНОГО gender)
            consolidated_frequencies = {}
            
            for lemma, variants in lemma_variants.items():
                with_gender = variants['with_gender']
                without_gender = variants['without_gender']
                
                if with_gender:
                    # Есть варианты с определённым родом - используем их и суммируем с вариантами без рода
                    for freq_key, freq in with_gender.items():
                        if freq_key not in consolidated_frequencies:
                            consolidated_frequencies[freq_key] = 0
                        consolidated_frequencies[freq_key] += freq
                    
                    # Добавляем частоты вариантов без рода к подходящим вариантам с родом
                    for freq_key_without, freq_without in without_gender.items():
                        # Находим вариант с тем же родом (если можно восстановить)
                        best_match = None
                        best_freq = 0
                        
                        for freq_key_with in with_gender.keys():
                            if with_gender[freq_key_with] > best_freq:
                                best_match = freq_key_with
                                best_freq = with_gender[freq_key_with]
                        
                        if best_match:
                            consolidated_frequencies[best_match] += freq_without
                        else:
                            # Если не нашли подходящий, оставляем без рода
                            consolidated_frequencies[freq_key_without] = freq_without
                else:
                    # Только варианты без рода - оставляем как есть
                    for freq_key, freq in without_gender.items():
                        consolidated_frequencies[freq_key] = freq
            
            # Добавляем не-существительные
            consolidated_frequencies.update(non_nouns)
            
            # Сортируем по частоте
            sorted_frequencies = sorted(consolidated_frequencies.items(), key=lambda x: x[1], reverse=True)
            
            # Создаём DataFrame только с НОВЫМИ (неизвестными) словами
            data = []
            for word_with_pos, freq in sorted_frequencies:
                # Извлекаем слово и часть речи из формата "слово (часть_речи)" или "el слово (часть_речи)"
                if ' (' in word_with_pos and word_with_pos.endswith(')'):
                    word_part = word_with_pos.split(' (')[0]  # "el capital" или "capital"
                    pos_tag = word_with_pos.split(' (')[1].rstrip(')')
                else:
                    word_part = word_with_pos
                    pos_tag = 'неизвестно'
                
                # Получаем базовую лемму из token_details (правильная лемматизация spaCy)
                base_lemma = word_part  # Fallback
                for safe_key, details in self.token_details.items():
                    if details['freq_key'] == word_with_pos:
                        base_lemma = safe_key[0]  # lemma из (lemma, pos, gender)
                        break
                
                # Проверяем, что слово НЕ известно в Anki
                is_known = False
                comment = ""
                
                if self.word_comparator:
                    # Попробуем lemma-aware проверку, если включено
                    if config.is_lemma_aware_known_enabled():
                        relevant_token_info = None
                        # Ищем точный freq_key (надёжнее для выбора POS/гендера)
                        for safe_key, details in self.token_details.items():
                            if details.get('freq_key') == word_with_pos:
                                relevant_token_info = details
                                break
                        if not relevant_token_info:
                            # Фолбэк: ищем по лемме
                            for safe_key, details in self.token_details.items():
                                if safe_key[0] == base_lemma:
                                    relevant_token_info = details
                                    break
                        pos_code = relevant_token_info.get('pos', None) if relevant_token_info else None
                        gender_code = relevant_token_info.get('gender', None) if relevant_token_info else None
                        is_known = self.word_comparator.is_token_known(
                            lemma=base_lemma,
                            pos=pos_code,
                            gender=gender_code
                        )
                    else:
                        # Строгая проверка точного слова как показывается
                        is_known = self.word_comparator.is_word_known(word_part)
                    
                    if not is_known:
                        # Получаем подсказки о похожих словах
                        relevant_token_info = None
                        for safe_key, details in self.token_details.items():
                            if safe_key[0] == base_lemma:  # lemma совпадает
                                relevant_token_info = details
                                break
                        similar = self.word_comparator.get_similar_candidates(
                            lemma=base_lemma,
                            pos=relevant_token_info.get('pos', 'UNKNOWN') if relevant_token_info else 'UNKNOWN',
                            gender=relevant_token_info.get('gender') if relevant_token_info else None
                        )
                        if similar:
                            comment = "Похожие в ANKI: " + ", ".join(similar)
                        else:
                            comment = "Новое слово"
                else:
                    # Fallback на старую проверку
                    is_known = self.is_word_known(word_part) or self.is_word_known(base_lemma)
                    comment = "ANKI недоступен" if not is_known else ""
                
                # Добавляем только неизвестные слова с достаточной длиной
                if not is_known and len(base_lemma) >= self.min_word_length:
                    # Вычисляем относительную частоту (процент от общего количества слов)
                    relative_frequency = (freq / total_words) * 100 if total_words > 0 else 0
                    
                    # === ПРАВИЛЬНОЕ ОПРЕДЕЛЕНИЕ GENDER ИЗ WORD (по правилу) ===
                    # Вычисляем Gender из итогового Word, а не из token_details
                    if word_part.startswith(("el ", "los ")):
                        gender = "Masc"
                    elif word_part.startswith(("la ", "las ")):
                        gender = "Fem"
                    else:
                        gender = "-"
                    
                    row = {
                        'Word': word_part,  # С артиклем для существительных
                        'Lemma': base_lemma,  # Базовая лемма без артикля
                        'Part of Speech': pos_tag,
                        'Gender': gender,  # Берём из word_part, не из token_details
                        'Frequency': f"{relative_frequency:.{decimal_places}f}%",
                        'Count': freq,
                        'Comments': comment or '-'
                    }
                    data.append(row)
            
            df = pd.DataFrame(data)
            logger.debug(f"Экспорт в Excel: сформирован DataFrame (rows={len(df)})")
            
            # Схлопываем по словам: для каждого уникального слова оставляем строку
            # с максимальным значением Count (дедупликация как в exporter.py)
            try:
                before_count = len(df)
                # Сортируем по слову (asc), затем по Count (desc) для детерминированности
                df = df.sort_values(['Word', 'Count'], ascending=[True, False], kind='stable')
                # Удаляем дубликаты слов, оставляя первую (с максимальным Count)
                df = df.drop_duplicates(subset=['Word'], keep='first').reset_index(drop=True)
                after_count = len(df)
                if after_count < before_count:
                    logger.info(f"Схлопнуто по словам: было {before_count}, осталось {after_count}")
            except Exception as e:
                # В случае неожиданных проблем со схлопыванием — не прерываем экспорт
                logger.warning(f"Не удалось схлопнуть по словам: {e}")
            
            # Финальная сортировка по убыванию Count для удобства пользователя
            df = df.sort_values('Count', ascending=False).reset_index(drop=True)
            
            # Создаём Excel writer с одним листом
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Только основной лист с обновлённой структурой
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            logger.info(f"Статистика экспортирована в {file_path}")
            logger.info(f"Экспортировано {len(data)} новых слов (из {len(self.word_frequencies)} всего)")
            logger.debug(f"Экспорт в Excel: завершён (dt={_time.time()-_t0:.2f}s)")
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте в Excel: {e}")
    
    
    def reset(self) -> None:
        """Сбрасывает всю статистику"""
        self.word_frequencies.clear()
        self.word_categories.clear()
        self.word_pos_tags.clear()
        logger.info("Статистика слов сброшена")
