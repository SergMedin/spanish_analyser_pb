"""
Модуль для обработки испанского текста

Содержит функции для:
- Определения доминирующего языка в тексте
- Удаления HTML тегов
- Очистки текста от префиксов
"""

import re
from bs4 import BeautifulSoup
from typing import Tuple, List
from .config import config


class SpanishTextProcessor:
    """Класс для обработки испанского текста"""
    
    def __init__(self) -> None:
        # Множества букв испанского алфавита и кириллицы
        self.spanish_alphabet = set("abcdefghijklmnñopqrstuvwxyzáéíóúü")
        self.cyrillic_alphabet = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")
        # Минимальная длина слова для извлечения берётся из конфигурации,
        # чтобы синхронизировать поведение с анализатором слов и экспортом.
        self.min_word_length = config.get_min_word_length()
        
        # Префиксы для удаления
        self.spanish_prefixes = [
            "los ", "los\xa0", "los&nbsp;",
            "las ", "las\xa0", "las&nbsp;",
            "la ", "la\xa0", "la&nbsp;",
            "el ", "el\xa0", "el&nbsp;",
        ]
    
    def get_spanish_dominant_string(self, str1: str, str2: str) -> str:
        """
        Определяет, какая из двух строк больше содержит испанских букв
        
        Args:
            str1: Первая строка для сравнения
            str2: Вторая строка для сравнения
            
        Returns:
            Строка с большим количеством испанских букв
        """
        def share_letters_in_alphabet(s: str, alphabet: set) -> float:
            """Подсчитывает долю букв, принадлежащих определённому алфавиту"""
            if not s:
                return 0.0
            return sum(1 for char in s.lower() if char in alphabet) / len(s)
        
        # Подсчёт букв для обеих строк
        spanish_count_str1 = share_letters_in_alphabet(str1, self.spanish_alphabet)
        cyrillic_count_str1 = share_letters_in_alphabet(str1, self.cyrillic_alphabet)
        
        spanish_count_str2 = share_letters_in_alphabet(str2, self.spanish_alphabet)
        cyrillic_count_str2 = share_letters_in_alphabet(str2, self.cyrillic_alphabet)
        
        # Сравнение количества букв
        if spanish_count_str1 > cyrillic_count_str1 and spanish_count_str1 > spanish_count_str2:
            return str1
        elif spanish_count_str2 > cyrillic_count_str2 and spanish_count_str2 > spanish_count_str1:
            return str2
        else:
            return str1
    
    def remove_spanish_prefixes(self, text: str) -> str:
        """
        Удаляет испанские артикли из начала текста
        
        Args:
            text: Исходный текст
            
        Returns:
            Текст без артиклей
        """
        text_lower = text.lower()
        for prefix in self.spanish_prefixes:
            if text_lower.startswith(prefix):
                return text[len(prefix):]
        return text
    
    def remove_html_tags(self, text: str) -> str:
        """
        Удаляет HTML теги из текста используя BeautifulSoup
        
        Args:
            text: HTML текст
            
        Returns:
            Очищенный текст без HTML тегов
        """
        if not text:
            return ""
        
        # Проверяем, содержит ли текст HTML теги
        if '<' in text and '>' in text:
            soup = BeautifulSoup(text, "html.parser")
            return soup.get_text()
        else:
            # Если текст не содержит HTML, возвращаем как есть
            return text
    
    def clean_text(self, text: str, remove_prefixes: bool = True) -> str:
        """
        Полная очистка текста от HTML тегов и опционально от префиксов
        
        Args:
            text: Исходный текст
            remove_prefixes: Удалять ли испанские префиксы
            
        Returns:
            Очищенный текст
        """
        cleaned_text = self.remove_html_tags(text)
        if remove_prefixes:
            cleaned_text = self.remove_spanish_prefixes(cleaned_text)
        return cleaned_text.strip()
    
    def extract_spanish_words(self, text: str) -> List[str]:
        """
        Извлекает испанские слова из текста
        
        Args:
            text: Исходный текст
            
        Returns:
            Список испанских слов
        """
        # Простая логика извлечения слов - можно улучшить
        if not text:
            return []
        # Разбиваем по пробелам и фильтруем
        words = text.lower().split()
        # Очищаем слова от знаков препинации и фильтруем по длине
        clean_words = []
        for word in words:
            clean_word = ''.join(c for c in word if c.isalpha() or c in 'áéíóúüñ')
            # Используем глобальную настройку минимальной длины слова
            if len(clean_word) >= self.min_word_length:
                clean_words.append(clean_word)
        return clean_words
