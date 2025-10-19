"""
Компонент для сравнения слов с известными.

Отвечает за загрузку известных слов из Anki, проверку известности
и фильтрацию только неизвестных слов для изучения.
"""

import os
import sqlite3
from typing import List, Dict, Set, Union, Optional, Tuple
from pathlib import Path
from ..interfaces.text_processor import WordComparatorInterface
from ..config import config
from ..cache import CacheManager  # Менеджер с поддержкой подпапок
from .normalizer import WordNormalizer
from .anki_connector import AnkiConnector
import time
import re

try:
    import spacy
except Exception:
    spacy = None  # type: ignore


import logging


logger = logging.getLogger(__name__)


class WordComparator(WordComparatorInterface):
    """Компаратор для сравнения слов с известными."""
    
    def __init__(self, collection_path: Optional[str] = None, deck_pattern: str = "Spanish", text_model: Optional["BaseTextModel"] = None, autoload: bool = True):
        """
        Инициализирует компаратор слов.
        
        Args:
            collection_path: Путь к базе данных Anki (устарел, используется AnkiConnect)
            deck_pattern: Паттерн для поиска испанских колод
        """
        self.collection_path = collection_path or self._get_default_collection_path()
        self.deck_pattern = deck_pattern
        self.known_words: Set[str] = set()  # точные слова (в нижнем регистре)
        self.normalized_known_words: Set[str] = set()  # сохраняем, но не используем для строгой проверки
        self.known_phrases: Set[str] = set()  # точные строки полей (в нижнем регистре)
        # Индексы на основе spaCy (если доступен):
        # NOUN с родом: (lemma_lower, gender) → присутствует в ANKI
        self.known_noun_lemma_gender: Set[Tuple[str, str]] = set()
        # Остальные POS: (lemma_lower, pos) → присутствует в ANKI
        self.known_lemma_pos: Set[Tuple[str, str]] = set()
        self.normalizer = WordNormalizer(use_cache=True)
        self._nlp = None
        self.anki_connector = AnkiConnector()
        self._text_model = text_model
        
        # Загружаем известные слова при инициализации (можно отключить для отложенной загрузки)
        if autoload:
            self._load_known_words_modern()
    
    def _load_known_words_modern(self) -> None:
        """
        Загружает известные слова через современный AnkiConnect API.
        """
        try:
            if not self.anki_connector.is_available():
                logger.warning("🔗 AnkiConnect недоступен")
                logger.info("💡 Для подключения к Anki:")
                logger.info("   1. Запустите Anki")
                logger.info("   2. Установите плагин AnkiConnect (код: 2055492159)")
                logger.info("   3. Перезапустите Anki")
                return
            
            logger.info("📥 Загружаем известные слова из Anki...")
            # Получаем все слова из испанских колод
            logger.debug(f"🔍 Запрашиваем слова с паттерном колоды: '{self.deck_pattern}'")
            spanish_words = self.anki_connector.extract_all_spanish_words(self.deck_pattern)
            
            if spanish_words:
                logger.debug(f"🔧 Подготовка известных слов: получено {len(spanish_words)} элементов. Начинаю индексацию…")
                _t0 = time.time()
                self._load_from_list(list(spanish_words))
                logger.debug(f"🔧 Индексация известных слов завершена (dt={time.time()-_t0:.2f}s)")
                logger.info(f"Загружено {len(self.known_words)} слов из Anki через AnkiConnect")
                
            else:
                logger.warning(f"Слова из испанских колод не найдены (паттерн: {self.deck_pattern})")
                
        except Exception as e:
            logger.error(f"Ошибка загрузки через AnkiConnect: {e}")
    
    def _get_default_collection_path(self) -> str:
        """Возвращает путь к базе Anki по умолчанию."""
        # Стандартные пути для разных ОС
        home = os.path.expanduser("~")
        
        if os.name == 'nt':  # Windows
            return os.path.join(home, "AppData", "Roaming", "Anki2", "User 1", "collection.anki2")
        elif os.name == 'posix':  # macOS и Linux
            if os.path.exists(os.path.join(home, "Library")):  # macOS
                return os.path.join(home, "Library", "Application Support", "Anki2", "User 1", "collection.anki2")
            else:  # Linux
                return os.path.join(home, ".local", "share", "Anki2", "User 1", "collection.anki2")
        
        return ""
    
    def load_known_words(self, source: Union[str, Path, List[str]]) -> None:
        """
        Загружает известные слова из источника.
        
        Args:
            source: Источник слов (путь к Anki или список слов)
        """
        if isinstance(source, list):
            self._load_from_list(source)
        else:
            # Попробуем кэш
            collection_path_str = str(source)
            if config.should_cache_anki_words() and os.path.exists(collection_path_str):
                try:
                    mtime = os.path.getmtime(collection_path_str)
                    size = os.path.getsize(collection_path_str)
                    cache_key = f"anki_known_words:{collection_path_str}:{mtime}:{size}:{self.deck_pattern}"
                    cache = CacheManager.get_cache()
                    cached = cache.get(cache_key)
                    if cached is not None and isinstance(cached, dict):
                        self.known_words = set(cached.get("known_words", []))
                        self.normalized_known_words = set(cached.get("normalized_known_words", []))
                        return
                except Exception:
                    pass
            self._load_from_anki(collection_path_str)
            if config.should_cache_anki_words() and os.path.exists(collection_path_str):
                try:
                    cache.set(cache_key, {
                        "known_words": list(self.known_words),
                        "normalized_known_words": list(self.normalized_known_words),
                    })
                except Exception:
                    pass
    
    def _load_from_list(self, words: List[str]) -> None:
        """
        Загружает слова из списка.
        
        Args:
            words: Список известных слов
        """
        logger.debug(f"🔧 Подготовка известных слов: старт (items_in={len(words)})")
        _t_start = time.time()
        self.known_words.clear()
        self.normalized_known_words.clear()
        self.known_phrases.clear()
        self.known_noun_lemma_gender.clear()
        self.known_lemma_pos.clear()
        
        # Принимаем, что words уже отдельные слова; дополнительно сохраняем точные формы
        _t_norm = time.time()
        for word in words:
            if word and isinstance(word, str):
                w = word.lower().strip()
                if not w:
                    continue
                self.known_words.add(w)
                normalized = self.normalizer.normalize(word)
                if normalized:
                    self.normalized_known_words.add(normalized)
        logger.debug(f"🔧 Подготовка известных слов: нормализация завершена (unique={len(self.known_words)}, dt={time.time()-_t_norm:.2f}s)")

        # Построим индексы лемм+POS из известных слов
        # ИСПРАВЛЕНИЕ: анализируем каждое слово отдельно, а не все сразу
        try:
            if self._text_model is not None:
                _t_idx = time.time()
                logger.debug("🔎 Индексация известных слов через text_model (по одному)…")
                for word in sorted(self.known_words):
                    if not word.strip():
                        continue
                    try:
                        result = self._text_model.analyze_text(word)
                        for tok in result.tokens:
                            lemma = (tok.lemma or "").lower()
                            pos = tok.pos or ""
                            if pos == 'NOUN':
                                # Без морфологии — помечаем Unknown
                                self.known_noun_lemma_gender.add((lemma, 'Unknown'))
                            else:
                                self.known_lemma_pos.add((lemma, pos))
                    except Exception as e:
                        logger.debug(f"Ошибка индексации '{word}': {e}")
                logger.debug(f"🔎 Индексация через text_model завершена (dt={time.time()-_t_idx:.2f}s)")
            elif spacy is not None:
                # Единая модель через SpacyManager
                from .spacy_manager import SpacyManager
                if self._nlp is None:
                    self._nlp = SpacyManager().get_nlp()
                _t_spa = time.time()
                logger.debug(f"🔎 Индексация известных слов через spaCy (по одному)… (model={getattr(self._nlp, 'meta', {}).get('name', 'unknown')}, items={len(self.known_words)})")
                _noun_count = 0
                _processed_words = 0
                
                for word in sorted(self.known_words):
                    if not word.strip():
                        continue
                    try:
                        doc = self._nlp(word)
                        _processed_words += 1
                        
                        for token in doc:
                            if not token.text.strip():
                                continue
                            lemma = token.lemma_.lower()
                            pos = token.pos_
                            if pos == 'NOUN' or pos == 'PROPN':
                                # PROPN обрабатываем как NOUN для консистентности (согласно правилам проекта)
                                gender_list = token.morph.get('Gender')
                                gender = gender_list[0] if gender_list else 'Unknown'
                                self.known_noun_lemma_gender.add((lemma, gender))
                                _noun_count += 1
                                
                            else:
                                self.known_lemma_pos.add((lemma, pos))
                    except Exception as e:
                        logger.debug(f"Ошибка индексации spaCy '{word}': {e}")
                logger.debug(f"🔎 Индексация spaCy завершена (processed={_processed_words}, nouns={_noun_count})")
        except Exception:
            # Не критично для работы
            pass
        finally:
            logger.debug(f"🔧 Подготовка известных слов: завершена (total_dt={time.time()-_t_start:.2f}s)")
    
    def _load_from_anki(self, collection_path: str) -> None:
        """
        Загружает известные слова из базы Anki.
        
        Args:
            collection_path: Путь к базе данных Anki
        """
        if not os.path.exists(collection_path):
            print(f"База Anki не найдена: {collection_path}")
            return
        
        try:
            # Создаем временную копию базы для чтения
            temp_path = collection_path + "-temp"
            with open(collection_path, 'rb') as src, open(temp_path, 'wb') as dst:
                dst.write(src.read())
            
            # Подключаемся к временной базе
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            
            # Ищем испанские колоды
            cursor.execute("""
                SELECT name FROM col WHERE decks LIKE ?
            """, (f'%{self.deck_pattern}%',))
            
            deck_names = cursor.fetchall()
            if not deck_names:
                print(f"Испанские колоды не найдены по паттерну: {self.deck_pattern}")
                return
            
            # Получаем ID колод
            deck_ids = []
            for deck_name in deck_names:
                cursor.execute("""
                    SELECT decks FROM col
                """)
                decks_data = cursor.fetchone()
                if decks_data:
                    # Парсим JSON с колодами
                    import json
                    try:
                        decks = json.loads(decks_data[0])
                        for deck_id, deck_info in decks.items():
                            if self.deck_pattern.replace('*', '') in deck_info.get('name', ''):
                                deck_ids.append(deck_id)
                    except json.JSONDecodeError:
                        continue
            
            # Получаем слова и фразы из найденных колод
            known_words = set()
            for deck_id in deck_ids:
                cursor.execute("""
                    SELECT flds FROM notes n
                    JOIN cards c ON n.id = c.nid
                    WHERE c.did = ?
                """, (deck_id,))
                
                for (flds,) in cursor.fetchall():
                    if flds:
                        # Парсим поля карточки
                        fields = flds.split('\x1f')
                        for field in fields:
                            if field:
                                # Сохраняем полную фразу как есть (строгое сравнение, в нижнем регистре)
                                field_norm = field.strip().lower()
                                if field_norm:
                                    self.known_phrases.add(field_norm)
                                # Извлекаем слова из поля
                                words = self._extract_words_from_field(field)
                                known_words.update(words)
            
            conn.close()
            os.remove(temp_path)
            
            # Обновляем внутренние множества
            self._load_from_list(list(known_words))
            
            logger.info(f"Загружено {len(self.known_words)} известных слов из Anki")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки слов из Anki: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def _extract_words_from_field(self, field: str) -> List[str]:
        """
        Извлекает слова из поля карточки Anki.
        
        Args:
            field: Содержимое поля карточки
            
        Returns:
            Список извлечённых слов
        """
        if not field:
            return []
        
        # Простое извлечение слов (можно улучшить)
        words = re.findall(r'\b[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]+\b', field)
        return [word.lower() for word in words if len(word) >= 3]
    
    def is_word_known(self, word: str, phrase: Optional[str] = None) -> bool:
        """
        Проверяет, известно ли слово.
        
        Args:
            word: Слово для проверки
            
        Returns:
            True если слово известно
        """
        if not word:
            return False
        
        word_lower = word.lower().strip()
        
        # 1. Проверяем ТОЛЬКО точное совпадение с терминами (строгая логика)
        # Нахождение слова внутри фразы НЕ делает его известным
        if word_lower in self.known_words:
            return True
        
        # 2. Проверяем точное совпадение фразы (если передана)
        if phrase:
            phrase_lower = phrase.lower().strip()
            if phrase_lower in self.known_phrases:
                return True
        
        # 3. Опционально: режим известности по лемме/части речи
        try:
            if config.is_lemma_aware_known_enabled():
                analysis_text = word_lower
                lemma = None
                pos = None
                if self._text_model is not None:
                    res = self._text_model.analyze_text(analysis_text)
                    if res.tokens:
                        lemma = (res.tokens[0].lemma or '').lower()
                        pos = res.tokens[0].pos or ''
                elif spacy is not None:
                    # Единая модель через SpacyManager
                    from .spacy_manager import SpacyManager
                    if self._nlp is None:
                        self._nlp = SpacyManager().get_nlp()
                    doc = self._nlp(analysis_text)
                    if doc:
                        lemma = doc[0].lemma_.lower()
                        pos = doc[0].pos_
                if lemma and pos:
                    if pos == 'NOUN':
                        # Если есть лемма существительного с любым родом
                        if (lemma, 'Masc') in self.known_noun_lemma_gender or (lemma, 'Fem') in self.known_noun_lemma_gender or (lemma, 'Unknown') in self.known_noun_lemma_gender:
                            return True
                    else:
                        if (lemma, pos) in self.known_lemma_pos:
                            return True
        except Exception:
            pass

        return False

    def is_token_known(self, *, lemma: Optional[str], pos: Optional[str] = None, gender: Optional[str] = None) -> bool:
        """
        Проверка известности на основе (lemma, pos, gender) без повторного вызова spaCy.

        Args:
            lemma: Лемма слова (нижний регистр)
            pos: POS-тег spaCy (например, 'NOUN', 'VERB')
            gender: Род для существительных ('Masc'|'Fem'|'Unknown'|None)

        Returns:
            True если комбинация известна по индексам ANKI
        """
        try:
            if not lemma:
                logger.debug(f"🚫 is_token_known: пустая lemma")
                return False
            lemma_l = lemma.lower().strip()
            logger.debug(f"🔎 is_token_known: lemma='{lemma_l}', pos={pos}, gender={gender}")
            
            # Сначала прямое совпадение среди точных терминов (как есть)
            if lemma_l in self.known_words:
                logger.debug(f"✅ is_token_known: найдено в known_words: '{lemma_l}'")
                return True
                
            if not pos:
                logger.debug(f"🚫 is_token_known: нет POS для '{lemma_l}'")
                return False
                
            if pos == 'NOUN':
                logger.debug(f"📝 Проверяем существительное: '{lemma_l}' с gender={gender}")
                
                # Любой из известных родов для данной леммы делает её известной
                masc_known = (lemma_l, 'Masc') in self.known_noun_lemma_gender
                fem_known = (lemma_l, 'Fem') in self.known_noun_lemma_gender
                unk_known = (lemma_l, 'Unknown') in self.known_noun_lemma_gender
                
                logger.debug(f"   ℹ️ Проверка в known_noun_lemma_gender: Masc={masc_known}, Fem={fem_known}, Unknown={unk_known}")
                
                if masc_known or fem_known or unk_known:
                    logger.debug(f"✅ is_token_known: найдено существительное '{lemma_l}' в known_noun_lemma_gender")
                    return True
                    
                # Если gender явно передан — проверим конкретику
                if gender in ('Masc', 'Fem', 'Unknown'):
                    specific_known = (lemma_l, gender) in self.known_noun_lemma_gender
                    logger.debug(f"   ℹ️ Конкретная проверка ({lemma_l}, {gender}): {specific_known}")
                    return specific_known
                    
                logger.debug(f"❌ is_token_known: существительное '{lemma_l}' не найдено")
                return False
            else:
                # Не-существительные
                lemma_pos_known = (lemma_l, pos) in self.known_lemma_pos
                logger.debug(f"   ℹ️ Проверка в known_lemma_pos ({lemma_l}, {pos}): {lemma_pos_known}")
                
                if lemma_pos_known:
                    logger.debug(f"✅ is_token_known: найдено в known_lemma_pos: ({lemma_l}, {pos})")
                else:
                    logger.debug(f"❌ is_token_known: не найдено в known_lemma_pos: ({lemma_l}, {pos})")
                
                return lemma_pos_known
        except Exception as e:
            logger.debug(f"❌ is_token_known ошибка: {e}")
            return False
    
    def filter_unknown_words(self, words: List[str]) -> List[str]:
        """
        Фильтрует только неизвестные слова.
        
        Args:
            words: Список слов для фильтрации
            
        Returns:
            Список только неизвестных слов
        """
        if not words:
            return []
        
        unknown_words = []
        for word in words:
            if not self.is_word_known(word):
                unknown_words.append(word)
        
        return unknown_words

    # --- Подсказки (не делают слово «известным») ---
    def get_similar_candidates(self, *, lemma: Optional[str], pos: Optional[str], gender: Optional[str]) -> List[str]:
        """
        Возвращает список «похожих» кандидатов из ANKI по лемме и морфологии.

        Это используется только для комментариев в отчётах и не влияет на строгую проверку
        известности. Диакритики сохраняются, никаких ручных правил испанского не применяется.
        """
        if not lemma:
            return []
        lemma_l = lemma.lower().strip()
        suggestions: List[str] = []
        
        try:
            # 1. Точное совпадение с леммой
            if lemma_l in self.known_words:
                suggestions.append(lemma_l)
            
            # 2. Если точного совпадения нет, ищем слова, которые содержат лемму как корень
            if not suggestions:
                # Ищем слова, которые начинаются с нашей леммы (но не точные совпадения)
                candidates = []
                for known_word in self.known_words:
                    if known_word.startswith(lemma_l) and known_word != lemma_l:
                        candidates.append(known_word)
                
                # Сортируем по длине - ближайшие формы первыми  
                candidates.sort(key=len)
                suggestions.extend(candidates[:3])
            
            # 3. Если это возвратный глагол (с 'se'), ищем базовую форму
            if not suggestions and lemma_l.endswith('se') and len(lemma_l) > 3:
                base_verb = lemma_l[:-2]  # убираем 'se'
                if base_verb in self.known_words:
                    suggestions.append(base_verb)
                else:
                    # Ищем формы базового глагола
                    for known_word in self.known_words:
                        if known_word.startswith(base_verb) and known_word != base_verb:
                            suggestions.append(known_word)
                            if len(suggestions) >= 2:
                                break
            
            # 4. Для существительных НЕ создаём синтетические комбинации
            # Показываем только РЕАЛЬНО существующие термины из ANKI
            # spaCy-индексы могут содержать артефакты от анализа сложных фраз
            
        except Exception:
            return []
        
        return suggestions[:5]
    
    def get_known_words_count(self) -> int:
        """
        Возвращает количество известных слов.
        
        Returns:
            Количество известных слов
        """
        return len(self.known_words)
    
    def get_known_words_sample(self, n: int = 10) -> List[str]:
        """
        Возвращает образец известных слов.
        
        Args:
            n: Количество слов для возврата
            
        Returns:
            Список известных слов
        """
        return list(self.known_words)[:n]
    
    def add_known_word(self, word: str) -> None:
        """
        Добавляет слово в список известных.
        
        Args:
            word: Слово для добавления
        """
        if word and isinstance(word, str):
            word_lower = word.lower().strip()
            self.known_words.add(word_lower)
            
            normalized = self.normalizer.normalize(word)
            if normalized:
                self.normalized_known_words.add(normalized)
    
    def remove_known_word(self, word: str) -> None:
        """
        Удаляет слово из списка известных.
        
        Args:
            word: Слово для удаления
        """
        if word:
            word_lower = word.lower().strip()
            self.known_words.discard(word_lower)
            
            normalized = self.normalizer.normalize(word)
            if normalized:
                self.normalized_known_words.discard(normalized)
    
    def get_comparison_statistics(self) -> Dict[str, int]:
        """
        Возвращает статистику сравнения.
        
        Returns:
            Словарь со статистикой
        """
        return {
            'known_words_count': len(self.known_words),
            'normalized_known_words_count': len(self.normalized_known_words),
            'collection_path': self.collection_path,
            'deck_pattern': self.deck_pattern
        }
    
    def reload_known_words(self) -> bool:
        """
        Перезагружает известные слова из Anki.
        
        Returns:
            True если перезагрузка прошла успешно
        """
        if self.collection_path and os.path.exists(self.collection_path):
            self.load_known_words(self.collection_path)
            return True
        return False
