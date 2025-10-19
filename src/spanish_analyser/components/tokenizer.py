"""
Компонент для токенизации испанского текста.

Отвечает за разбивку текста на токены, валидацию и фильтрацию.
"""

import re
import unicodedata
from typing import List
from ..interfaces.text_processor import TokenProcessorInterface


class TokenProcessor(TokenProcessorInterface):
    """Процессор для токенизации испанского текста."""
    
    def __init__(self, min_length: int = 3, include_numbers: bool = False):
        """
        Инициализирует процессор токенизации.
        
        Args:
            min_length: Минимальная длина токена
            include_numbers: Включать ли числа в токены
        """
        self.min_length = min_length
        self.include_numbers = include_numbers
        
        # Паттерн для испанских слов (включая акценты)
        if include_numbers:
            self.word_pattern = re.compile(r'[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ0-9]+')
        else:
            self.word_pattern = re.compile(r'[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]+')
    
    def tokenize(self, text: str) -> List[str]:
        """
        Разбивает текст на токены.
        
        Args:
            text: Исходный текст
            
        Returns:
            Список токенов
        """
        if not text or not text.strip():
            return []
        # Единая Unicode-нормализация (NFC) до разбиения
        text = unicodedata.normalize('NFC', text)
        
        # Разбиваем на слова по пробелам и знакам препинания
        tokens = re.findall(self.word_pattern, text)
        
        # Фильтруем токены
        filtered_tokens = self.filter_tokens(tokens)
        
        return filtered_tokens
    
    def is_valid_token(self, token: str) -> bool:
        """
        Проверяет валидность токена.
        
        Args:
            token: Токен для проверки
            
        Returns:
            True если токен валиден
        """
        if not token:
            return False
        
        # Если включены числа, то для числовых токенов минимальная длина = 1
        if self.include_numbers and token.isdigit():
            min_len = 1
        else:
            min_len = self.min_length
        
        # Проверяем минимальную длину
        if len(token) < min_len:
            return False
        
        # Если включены числа, то токен должен содержать либо букву, либо цифру
        if self.include_numbers:
            if not re.search(r'[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ0-9]', token):
                return False
        else:
            # Проверяем, что токен содержит хотя бы одну букву
            if not re.search(r'[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]', token):
                return False
        
        return True
    
    def filter_tokens(self, tokens: List[str]) -> List[str]:
        """
        Фильтрует токены по критериям валидности.
        
        Args:
            tokens: Список токенов для фильтрации
            
        Returns:
            Отфильтрованный список токенов
        """
        if not tokens:
            return []
        
        # Приводим к нижнему регистру и фильтруем
        filtered = []
        for token in tokens:
            token_lower = token.lower()
            if self.is_valid_token(token_lower):
                filtered.append(token_lower)
        
        return filtered
    
    def get_token_statistics(self, tokens: List[str]) -> dict:
        """
        Возвращает статистику по токенам.
        
        Args:
            tokens: Список токенов
            
        Returns:
            Словарь со статистикой
        """
        if not tokens:
            return {
                'total_tokens': 0,
                'valid_tokens': 0,
                'avg_length': 0.0,
                'length_distribution': {}
            }
        
        # Если токены уже отфильтрованы, используем их как есть
        # Иначе фильтруем по валидности
        if all(self.is_valid_token(t) for t in tokens):
            valid_tokens = tokens
        else:
            valid_tokens = [t for t in tokens if self.is_valid_token(t)]
        
        lengths = [len(t) for t in valid_tokens]
        
        # Распределение по длинам
        length_dist = {}
        for length in lengths:
            length_dist[length] = length_dist.get(length, 0) + 1
        
        return {
            'total_tokens': len(tokens),
            'valid_tokens': len(valid_tokens),
            'avg_length': round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
            'length_distribution': length_dist
        }
