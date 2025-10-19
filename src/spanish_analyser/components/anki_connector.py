"""
Современный компонент для интеграции с Anki через AnkiConnect.

Использует HTTP API AnkiConnect для надежного взаимодействия с Anki.
Рекомендованный подход для интеграции с Anki в 2024 году.
"""

import json
import urllib.request
import urllib.error
from typing import List, Dict, Set, Optional, Any
from ..config import config
from ..cache import CacheManager  # Менеджер с поддержкой подпапок
import time
import random
import logging
import unicodedata

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


logger = logging.getLogger(__name__)


class AnkiConnector:
    """Современный коннектор для взаимодействия с Anki через AnkiConnect."""
    
    def __init__(self, url: str = "http://localhost:8765"):
        """
        Инициализирует AnkiConnect клиент.
        
        Args:
            url: URL AnkiConnect API (по умолчанию localhost:8765)
        """
        self.url = url
        self.version = 6
        self._is_available = None
        
    def invoke(self, action: str, params: Optional[Dict] = None) -> Any:
        """
        Отправляет запрос к AnkiConnect API.
        
        Args:
            action: Название действия (например, "deckNames")
            params: Параметры для действия
            
        Returns:
            Результат выполнения запроса
            
        Raises:
            Exception: Если произошла ошибка при выполнении запроса
        """
        request_data = {
            'action': action,
            'version': self.version,
            'params': params or {}
        }
        
        retries = 3
        last_err: Optional[Exception] = None
        for attempt in range(retries):
            try:
                request_json = json.dumps(request_data).encode('utf-8')
                req = urllib.request.Request(self.url, request_json)
                # Оптимизированные таймауты для быстрого отклика
                timeout = 30 if action in ['cardsInfo', 'notesInfo', 'findNotes'] else 15
                response = urllib.request.urlopen(req, timeout=timeout)
                response_data = json.load(response)

                if len(response_data) != 2:
                    raise Exception('Неожиданное количество полей в ответе AnkiConnect')

                if 'error' not in response_data or 'result' not in response_data:
                    raise Exception('Ответ не содержит ожидаемые поля')

                if response_data['error'] is not None:
                    raise Exception(f"Ошибка AnkiConnect: {response_data['error']}")

                return response_data['result']

            except (urllib.error.URLError, json.JSONDecodeError, Exception) as e:
                last_err = e
                if attempt < retries - 1:
                    backoff = (2 ** attempt) + random.uniform(0, 0.25)
                    logger.debug(f"Повтор AnkiConnect {action} через {backoff:.2f}s: {e}")
                    time.sleep(backoff)
                    continue
                break
        raise Exception(f"Ошибка AnkiConnect: {last_err}")
    
    def is_available(self) -> bool:
        """
        Проверяет доступность AnkiConnect.
        
        Returns:
            True если AnkiConnect доступен
        """
        if self._is_available is not None:
            return self._is_available
            
        try:
            # Простой запрос для проверки доступности
            result = self.invoke('version')
            self._is_available = isinstance(result, int) and result >= 6
            return self._is_available
        except Exception:
            self._is_available = False
            return False
    
    def get_deck_names(self) -> List[str]:
        """
        Получает список всех колод в Anki.
        
        Returns:
            Список названий колод
        """
        try:
            return self.invoke('deckNames') or []
        except Exception as e:
            logger.error(f"Ошибка получения колод: {e}")
            return []
    
    def find_spanish_decks(self, pattern: str = "Spanish") -> List[str]:
        """
        Находит испанские колоды по паттерну.
        
        Args:
            pattern: Паттерн для поиска (например, "Spanish")
            
        Returns:
            Список названий испанских колод
        """
        all_decks = self.get_deck_names()
        pattern_lower = pattern.lower().replace('*', '')
        
        spanish_decks = []
        for deck in all_decks:
            if pattern_lower in deck.lower():
                spanish_decks.append(deck)
                
        return spanish_decks
    
    def get_cards_from_deck(self, deck_name: str) -> List[int]:
        """
        Получает ID всех карточек из колоды.
        
        Args:
            deck_name: Название колоды
            
        Returns:
            Список ID карточек
        """
        try:
            query = f'deck:"{deck_name}"'
            return self.invoke('findCards', {'query': query}) or []
        except Exception as e:
            logger.error(f"Ошибка получения карточек из колоды {deck_name}: {e}")
            return []
    
    def get_notes_info(self, note_ids: List[int]) -> List[Dict]:
        """
        Получает информацию о заметках по их ID.
        
        Args:
            note_ids: Список ID заметок
            
        Returns:
            Список информации о заметках
        """
        try:
            if not note_ids:
                return []
            return self.invoke('notesInfo', {'notes': note_ids}) or []
        except Exception as e:
            logger.error(f"Ошибка получения информации о заметках: {e}")
            return []
    
    def get_cards_info(self, card_ids: List[int]) -> List[Dict]:
        """
        Получает информацию о карточках по их ID.
        
        Args:
            card_ids: Список ID карточек
            
        Returns:
            Список информации о карточках
        """
        try:
            if not card_ids:
                return []
            return self.invoke('cardsInfo', {'cards': card_ids}) or []
        except Exception as e:
            logger.error(f"Ошибка получения информации о карточках: {e}")
            return []
    
    def extract_all_spanish_words(self, deck_pattern: str = "Spanish") -> Set[str]:
        """
        Извлекает все испанские слова из колод используя прямой запрос как в Anki.
        
        Args:
            deck_pattern: Паттерн для поиска испанских колод (например, "Spanish")
            
        Returns:
            Множество всех слов из испанских колод
        """
        all_words = set()
        # Счётчик для выявления дубликатов терминов между разными заметками
        term_counts: Dict[str, int] = {}
        
        try:
            # Кэш по паттерну колоды (увеличенное время жизни для Anki данных)
            cache_key = f"anki_words:{deck_pattern}"
            cache = CacheManager.get_cache()
            cached = cache.get(cache_key)
            if cached and isinstance(cached, (set, list)):
                logger.info(f"✨ Используется кэш Anki: {len(cached)} слов (быстрая загрузка)")
                return set(cached)
            # Используем прямой запрос как в Anki: deck:Spanish*
            query = f"deck:{deck_pattern}*"
            logger.info(f"AnkiConnect запрос: {query}")
            
            # ИСПРАВЛЕНО: Работаем напрямую с заметками, а не с карточками
            logger.debug(f"🔍 Начинаем findNotes для запроса: {query}")
            start_time = time.time()
            all_note_ids = self.invoke('findNotes', {'query': query}) or []
            find_time = time.time() - start_time
            logger.debug(f"⏱️ findNotes завершен за {find_time:.2f}s, найдено IDs: {len(all_note_ids)}")
            
            if not all_note_ids:
                logger.warning(f"Заметки не найдены по запросу: {query}")
                return all_words
            
            logger.info(f"Найдено заметок: {len(all_note_ids)}")
            
            # Получаем информацию о заметках порциями для избежания таймаута
            batch_size = 100  # Уменьшенный размер пакета для быстрой обработки
            
            # Счётчики для детального отчёта
            processed_notes = 0
            notes_with_terms = 0
            notes_without_spanish_fields = 0
            notes_with_empty_fields = 0
            notes_with_short_terms = 0
            
            total_batches = (len(all_note_ids) + batch_size - 1) // batch_size
            logger.info(f"Обработка {len(all_note_ids)} заметок в {total_batches} пакетах по {batch_size}")
            
            # Создаём прогресс-бар согласно правилам UI, если tqdm доступен
            if tqdm:
                progress_bar = tqdm(
                    total=total_batches, 
                    desc="📥 Загрузка слов из Anki", 
                    unit="пакет",
                    ncols=80,  # Фиксированная ширина для стабильного отображения
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}'
                )
            else:
                progress_bar = None
            
            for batch_idx, i in enumerate(range(0, len(all_note_ids), batch_size)):
                batch_note_ids = all_note_ids[i:i + batch_size]
                batch_end = min(i + batch_size, len(all_note_ids))
                
                batch_start_time = time.time()
                logger.debug(f"🔄 Начинаем пакет {batch_idx+1}/{total_batches}: заметки {i+1}-{batch_end}")
                
                if progress_bar:
                    # Краткие подписи согласно правилам UI
                    progress_bar.set_postfix({
                        "Заметки": f"{i+1}-{batch_end}",
                        "Найдено": f"{len(all_words)}"
                    })
                else:
                    logger.info(f"📝 Обрабатываем заметки {i+1}-{batch_end} из {len(all_note_ids)} (пакет {batch_idx+1}/{total_batches})")
                
                try:
                    logger.debug(f"📡 Запрос notesInfo для {len(batch_note_ids)} заметок...")
                    notes_start = time.time()
                    notes_info = self.get_notes_info(batch_note_ids)
                    notes_time = time.time() - notes_start
                    logger.debug(f"📡 notesInfo завершен за {notes_time:.2f}s, получено {len(notes_info)} заметок")
                    
                    # Извлекаем термины из полей заметок (только испанские поля)
                    for note in notes_info:
                        processed_notes += 1
                        note_id = note.get('noteId', 'неизвестен')
                        fields = note.get('fields', {})
                        
                        # Проверяем наличие основных полей
                        front_text = fields.get('FrontText', {}).get('value', '') or fields.get('Front', {}).get('value', '')
                        back_text = fields.get('BackText', {}).get('value', '') or fields.get('Back', {}).get('value', '')
                        
                        if not front_text and not back_text:
                            notes_without_spanish_fields += 1
                            continue
                        
                        # Определяем, в каком поле находится испанский текст
                        spanish_field_location = self._detect_spanish_field(front_text, back_text)
                        spanish_text = front_text if spanish_field_location == 'front' else back_text

                        if not spanish_text or not spanish_text.strip():
                            notes_with_empty_fields += 1
                            continue
                            
                        logger.debug(f"📎 Обрабатываем карточку: '{spanish_text[:50]}{'...' if len(spanish_text) > 50 else '}'}")
                        
                        # Извлекаем термины из испанского поля
                        note_has_terms = False
                        terms = self._extract_terms_from_field(spanish_text)
                        if terms:
                            note_has_terms = True
                            for term in terms:
                                # Считаем количество вхождений термина (для отчёта о дубликатах)
                                term_counts[term] = term_counts.get(term, 0) + 1
                                # В множество попадает только одна уникальная форма
                                all_words.add(term)
                        else:
                            # Термины не извлечены - возможно, слишком короткие
                            import re
                            cleaned_text = re.sub(r'<[^>]+>', ' ', spanish_text).strip()
                            if cleaned_text and len(cleaned_text) < config.get_min_word_length():
                                # Текст есть, но слишком короткий
                                pass  # Будет учтён ниже
                        
                        if note_has_terms:
                            notes_with_terms += 1
                        else:
                            # Заметка не дала терминов - выясняем почему
                            if spanish_text and spanish_text.strip():
                                notes_with_short_terms += 1  # Есть контент, но термины короткие
                            else:
                                notes_with_empty_fields += 1  # Пустое испанское поле
                
                except Exception as e:
                    logger.debug(f"Ошибка при обработке пакета заметок: {e}")
                    continue
                finally:
                    batch_time = time.time() - batch_start_time
                    logger.debug(f"✅ Пакет {batch_idx+1} завершен за {batch_time:.2f}s, найдено слов: +{len(all_words) - len(term_counts) if len(all_words) >= len(term_counts) else 0}")
                    if progress_bar:
                        progress_bar.update(1)
            
            # Закрываем прогресс-бар
            if progress_bar:
                progress_bar.close()
            
            logger.info(f"Извлечено уникальных слов: {len(all_words)}")
            try:
                logger.debug(f"💾 Сохраняем {len(all_words)} слов в кэш с ключом: {cache_key}")
                cache_start = time.time()
                cache.set(cache_key, list(all_words))
                cache_time = time.time() - cache_start
                logger.debug(f"💾 Кэш сохранен за {cache_time:.2f}s")
            except Exception as e:
                logger.debug(f"⚠️ Ошибка сохранения в кэш: {e}")
                pass
            
            # === ДЕТАЛЬНЫЙ ОТЧЁТ ОБ ИСКЛЮЧЁННЫХ ЗАМЕТКАХ ===
            excluded_total = processed_notes - notes_with_terms
            if excluded_total > 0:
                logger.info("Детальный отчёт обработки заметок:")
                logger.info(f"  Всего найдено заметок: {len(all_note_ids)}")
                logger.info(f"  Обработано заметок: {processed_notes}")
                logger.info(f"  Заметки с извлечёнными терминами: {notes_with_terms}")
                logger.info(f"  Исключено заметок: {excluded_total}")
                
                if notes_without_spanish_fields > 0:
                    logger.info(f"  • Нет текстовых полей (FrontText/BackText): {notes_without_spanish_fields}")
                
                if notes_with_empty_fields > 0:
                    logger.info(f"  • Пустые поля с испанским текстом: {notes_with_empty_fields}")
                
                if notes_with_short_terms > 0:
                    min_length = config.get_min_word_length()
                    logger.info(f"  • Термины короче {min_length} символов: {notes_with_short_terms}")
                
                # Проверка на несоответствие счётчиков
                accounted = notes_without_spanish_fields + notes_with_empty_fields + notes_with_short_terms
                if excluded_total > accounted:
                    other_reasons = excluded_total - accounted
                    logger.info(f"  • Другие причины (ошибки обработки): {other_reasons}")
            
            # Отчёт о дубликатах (одни и те же термины, встречающиеся в нескольких заметках)
            duplicated = {t: c for t, c in term_counts.items() if c > 1}
            if duplicated:
                total_extra = sum(c - 1 for c in duplicated.values())
                logger.info(f"Дубликаты терминов в заметках: {len(duplicated)} (исключено повторных вхождений: {total_extra})")
                sample = sorted(duplicated.items(), key=lambda kv: kv[1], reverse=True)[:5]
                for term, cnt in sample:
                    logger.info(f"  - '{term}' → {cnt}")
        
        except Exception as e:
            logger.error(f"Ошибка извлечения слов из Anki: {e}")
        
        return all_words
    
    def _detect_spanish_field(self, front_text: str, back_text: str) -> str:
        """
        Определяет какое поле содержит испанский текст на основе доли латинских букв и цифр.
        
        Args:
            front_text: Текст поля FrontText
            back_text: Текст поля BackText
            
        Returns:
            'front' если испанский текст в FrontText, 'back' если в BackText
        """
        import re
        
        def calculate_latin_ratio(text: str) -> float:
            """Вычисляет долю латинских букв и цифр среди всех букв в тексте."""
            if not text:
                return 0.0
            
            # Удаляем HTML теги
            clean_text = re.sub(r'<[^>]+>', ' ', text)
            
            # Подсчитываем все буквы (любого алфавита)
            all_letters = re.findall(r'[a-zA-ZáéíóúñüÁÉÍÓÚÑÜа-яёА-ЯЁ]', clean_text)
            if not all_letters:
                return 0.0
            
            # Подсчитываем латинские буквы (включая испанские диакритики) и цифры
            latin_and_digits = re.findall(r'[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ0-9]', clean_text)
            
            return len(latin_and_digits) / len(all_letters)
        
        front_ratio = calculate_latin_ratio(front_text)
        back_ratio = calculate_latin_ratio(back_text)
        
        # Возвращаем поле с большей долей латинских символов
        return 'front' if front_ratio >= back_ratio else 'back'
    
    def _extract_terms_from_field(self, text: str) -> Set[str]:
        """
        Извлекает термины из поля карточки как цельные единицы изучения.
        
        ВАЖНО: Не разбивает на отдельные слова! Каждое поле FrontText - это один термин.
        
        Args:
            text: Текст поля карточки
            
        Returns:
            Множество терминов (цельных фраз/слов)
        """
        import re
        
        if not text:
            return set()
        
        # Удаляем HTML теги
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Единая Unicode-нормализация (NFC) для соответствия с анализом
        text = unicodedata.normalize('NFC', text)
        
        # Удаляем лишние пробелы и нормализуем
        text = re.sub(r'\s+', ' ', text).strip()
        
        if not text:
            return set()
        
        # Фильтруем по минимальной длине
        min_length = config.get_min_word_length()
        if len(text) >= min_length:
            return {text.lower()}
        
        return set()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Получает информацию о подключении к AnkiConnect.
        
        Returns:
            Словарь с информацией о подключении
        """
        info = {
            'url': self.url,
            'available': False,
            'version': None,
            'total_decks': 0,
            'spanish_decks': [],
            'error': None
        }
        
        try:
            if self.is_available():
                info['available'] = True
                info['version'] = self.invoke('version')
                info['total_decks'] = len(self.get_deck_names())
                info['spanish_decks'] = self.find_spanish_decks("Spanish")
            else:
                info['error'] = "AnkiConnect недоступен"
        except Exception as e:
            info['error'] = str(e)
        
        return info
