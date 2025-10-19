"""
Модуль для интеграции с Anki

Предоставляет функциональность для:
- Подключения к коллекции Anki
- Поиска заметок по колодам
- Извлечения текста из карточек
"""

import os
from typing import List, Dict, Any, Optional
from anki.storage import Collection
from .config import config
import logging

logger = logging.getLogger(__name__)


class AnkiIntegration:
    """Класс для интеграции с Anki"""
    
    def __init__(self, collection_path: str = None):
        """
        Инициализация интеграции с Anki
        
        Args:
            collection_path: Путь к файлу коллекции Anki (.anki2)
                           Если не указан, используется путь из конфигурации
        """
        self.collection_path = collection_path or config.get_collection_path()
        self.collection = None
        self._connected = False
    
    def __enter__(self):
        """Контекстный менеджер - вход"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        self.disconnect()
    
    def connect(self) -> bool:
        """
        Подключается к коллекции Anki
        
        Returns:
            True если подключение успешно, False в противном случае
        """
        try:
            if not os.path.exists(self.collection_path):
                logger.error(f"Файл коллекции не найден: {self.collection_path}")
                return False
            
            self.collection = Collection(self.collection_path)
            self._connected = True
            logger.info(f"Подключение к Anki успешно: {self.collection_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к Anki: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """Отключается от коллекции Anki"""
        if self.collection:
            try:
                self.collection.close()
                logger.info("Отключение от Anki успешно")
            except Exception as e:
                logger.warning(f"Ошибка при отключении от Anki: {e}")
            finally:
                self.collection = None
                self._connected = False
    
    def is_connected(self) -> bool:
        """
        Проверяет, подключены ли к Anki
        
        Returns:
            True если подключены, False в противном случае
        """
        return self._connected and self.collection is not None
    
    def get_deck_names(self) -> List[str]:
        """
        Получает список названий всех колод
        
        Returns:
            Список названий колод
        """
        if not self.is_connected():
            return []
        
        try:
            deck_names = [deck['name'] for deck in self.collection.decks.all()]
            return deck_names
        except Exception as e:
            logger.error(f"Ошибка получения названий колод: {e}")
            return []
    
    def find_notes_by_deck(self, deck_pattern: str = None) -> List[int]:
        """
        Находит заметки по паттерну названия колоды
        
        Args:
            deck_pattern: Паттерн для поиска колод (например, "Spanish*")
                        Если не указан, используется паттерн из конфигурации
        
        Returns:
            Список ID заметок
        """
        if not self.is_connected():
            return []
        
        deck_pattern = deck_pattern or config.get_deck_pattern()
        
        try:
            # Используем поиск Anki для поиска заметок в колодах по паттерну
            note_ids = self.collection.find_notes(f"deck:{deck_pattern}")
            return note_ids
        except Exception as e:
            logger.error(f"Ошибка поиска заметок по колоде {deck_pattern}: {e}")
            return []
    
    def extract_text_from_notes(self, note_ids: List[int], field_names: List[str] = None) -> List[Dict[str, Any]]:
        """
        Извлекает текст из заметок по указанным полям
        
        Args:
            note_ids: Список ID заметок
            field_names: Список названий полей для извлечения
                        Если не указан, используются поля из конфигурации
        
        Returns:
            Список словарей с данными заметок
        """
        if not self.is_connected():
            return []
        
        field_names = field_names or config.get_field_names()
        notes_data = []
        
        try:
            for note_id in note_ids:
                note = self.collection.get_note(note_id)
                note_data = {
                    'note_id': note_id,
                    'texts': []
                }
                
                # Получаем тип заметки и схему полей
                note_type = self.collection.models.get(note.mid)
                field_names_from_schema = note_type['flds']
                field_names_list = [field['name'] for field in field_names_from_schema]
                
                # Создаём словарь {название_поля: значение_поля}
                fields_dict = dict(zip(field_names_list, note.fields))
                
                # Сначала попробуем найти поля по точному названию
                found_fields = []
                for field_name in field_names:
                    if field_name in fields_dict:
                        field_text = fields_dict[field_name]
                        if field_text and field_text.strip():
                            note_data['texts'].append(field_text)
                            found_fields.append(field_name)
                
                # Если точные поля не найдены, используем логику выбора лучшего поля
                if not found_fields:
                    best_field_text = self._find_best_spanish_field(note)
                    if best_field_text:
                        note_data['texts'].append(best_field_text)
                
                notes_data.append(note_data)
                
        except Exception as e:
            logger.error(f"Ошибка извлечения текста из заметок: {e}")
        
        return notes_data
    
    def _contains_spanish_text(self, text: str) -> bool:
        """
        Проверяет, содержит ли текст испанские символы
        
        Args:
            text: Текст для проверки
            
        Returns:
            True если текст содержит испанские символы
        """
        if not text:
            return False
        
        # Простая проверка на испанские символы
        spanish_chars = set('áéíóúñüÁÉÍÓÚÑÜ')
        return any(char in spanish_chars for char in text)
    
    def _calculate_spanish_ratio(self, text: str) -> float:
        """
        Вычисляет долю испанских символов в тексте
        
        Args:
            text: Текст для анализа
            
        Returns:
            Доля испанских символов от 0.0 до 1.0
        """
        if not text or not text.strip():
            return 0.0
        
        # Расширенный набор испанских символов
        spanish_chars = set('áéíóúñüÁÉÍÓÚÑÜabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
        
        # Подсчитываем испанские символы
        spanish_count = sum(1 for char in text if char in spanish_chars)
        total_chars = len(text.strip())
        
        if total_chars == 0:
            return 0.0
        
        return spanish_count / total_chars
    
    def _find_best_spanish_field(self, note) -> str:
        """
        Находит поле с наибольшей долей испанского текста
        
        Args:
            note: Заметка Anki
            
        Returns:
            Текст из лучшего поля или пустая строка
        """
        if not note or not note.fields:
            return ""
        
        best_field_text = ""
        best_ratio = 0.0
        
        for field_text in note.fields:
            if field_text and field_text.strip():
                # Вычисляем долю испанского текста
                ratio = self._calculate_spanish_ratio(field_text)
                
                # Если это поле лучше предыдущего, обновляем
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_field_text = field_text
        
        # Возвращаем поле только если доля испанского текста достаточно высока
        # Порог берём из конфигурации
        min_spanish_ratio = config.get_min_spanish_ratio()
        if best_ratio >= min_spanish_ratio:
            return best_field_text
        
        return ""
    
    def get_note_count(self, deck_pattern: str = None) -> int:
        """
        Получает количество заметок в колоде
        
        Args:
            deck_pattern: Паттерн для поиска колоды
        
        Returns:
            Количество заметок
        """
        note_ids = self.find_notes_by_deck(deck_pattern)
        return len(note_ids)
    
    def get_deck_info(self, deck_pattern: str = None) -> Dict[str, Any]:
        """
        Получает информацию о колоде
        
        Args:
            deck_pattern: Паттерн для поиска колоды
        
        Returns:
            Словарь с информацией о колоде
        """
        deck_pattern = deck_pattern or config.get_deck_pattern()
        note_ids = self.find_notes_by_deck(deck_pattern)
        
        return {
            'deck_pattern': deck_pattern,
            'note_count': len(note_ids),
            'deck_names': self.get_deck_names()
        }
