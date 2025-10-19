"""
Тесты для компонента TokenProcessor.
"""

import pytest
from src.spanish_analyser.components.tokenizer import TokenProcessor


class TestTokenProcessor:
    """Тесты для TokenProcessor."""
    
    def test_init(self):
        """Тест инициализации."""
        processor = TokenProcessor()
        assert processor.min_length == 3
        assert processor.include_numbers is False
        
        processor = TokenProcessor(min_length=5, include_numbers=True)
        assert processor.min_length == 5
        assert processor.include_numbers is True
    
    def test_tokenize_empty_text(self):
        """Тест токенизации пустого текста."""
        processor = TokenProcessor()
        tokens = processor.tokenize("")
        assert tokens == []
        
        tokens = processor.tokenize("   ")
        assert tokens == []
        
        tokens = processor.tokenize(None)
        assert tokens == []
    
    def test_tokenize_simple_text(self):
        """Тест токенизации простого текста."""
        processor = TokenProcessor()
        text = "Hola mundo español"
        tokens = processor.tokenize(text)
        
        assert len(tokens) == 3
        assert "hola" in tokens
        assert "mundo" in tokens
        assert "español" in tokens
    
    def test_tokenize_with_accents(self):
        """Тест токенизации текста с акцентами."""
        processor = TokenProcessor()
        text = "El niño está aquí con la niña"
        tokens = processor.tokenize(text)
        
        assert "niño" in tokens
        assert "está" in tokens
        assert "aquí" in tokens
        assert "niña" in tokens
    
    def test_tokenize_with_punctuation(self):
        """Тест токенизации текста с пунктуацией."""
        processor = TokenProcessor()
        text = "¡Hola! ¿Cómo estás? Bien, gracias."
        tokens = processor.tokenize(text)
        
        assert "hola" in tokens
        assert "cómo" in tokens
        assert "estás" in tokens
        assert "bien" in tokens
        assert "gracias" in tokens
    
    def test_tokenize_with_numbers_disabled(self):
        """Тест токенизации без чисел."""
        processor = TokenProcessor(include_numbers=False)
        text = "Tengo 5 manzanas y 3 peras"
        tokens = processor.tokenize(text)
        
        assert "tengo" in tokens
        assert "manzanas" in tokens
        assert "peras" in tokens
        assert "5" not in tokens
        assert "3" not in tokens
    
    def test_tokenize_with_numbers_enabled(self):
        """Тест токенизации с числами."""
        processor = TokenProcessor(include_numbers=True)
        text = "Tengo 5 manzanas y 3 peras"
        tokens = processor.tokenize(text)
        
        assert "tengo" in tokens
        assert "manzanas" in tokens
        assert "peras" in tokens
        assert "5" in tokens
        assert "3" in tokens
    
    def test_is_valid_token(self):
        """Тест валидации токенов."""
        processor = TokenProcessor(min_length=3)
        
        # Валидные токены
        assert processor.is_valid_token("hola") is True
        assert processor.is_valid_token("mundo") is True
        assert processor.is_valid_token("español") is True
        
        # Невалидные токены
        assert processor.is_valid_token("") is False
        assert processor.is_valid_token("a") is False
        assert processor.is_valid_token("ab") is False
        assert processor.is_valid_token("123") is False
        assert processor.is_valid_token("!@#") is False
    
    def test_filter_tokens(self):
        """Тест фильтрации токенов."""
        processor = TokenProcessor(min_length=3)
        tokens = ["hola", "a", "mundo", "b", "español", "123", "!"]
        filtered = processor.filter_tokens(tokens)
        
        assert "hola" in filtered
        assert "mundo" in filtered
        assert "español" in filtered
        assert "a" not in filtered
        assert "b" not in filtered
        assert "123" not in filtered
        assert "!" not in filtered
    
    def test_get_token_statistics(self):
        """Тест получения статистики токенов."""
        processor = TokenProcessor(min_length=3)
        tokens = ["hola", "mundo", "español", "hola", "mundo"]
        stats = processor.get_token_statistics(tokens)
        
        assert stats['total_tokens'] == 5
        assert stats['valid_tokens'] == 5
        assert stats['avg_length'] == 5.0  # (4+5+7+4+5)/5
        assert stats['length_distribution'][4] == 2  # hola, hola
        assert stats['length_distribution'][5] == 2  # mundo, mundo
        assert stats['length_distribution'][7] == 1  # español
    
    def test_get_token_statistics_empty(self):
        """Тест статистики для пустого списка токенов."""
        processor = TokenProcessor()
        stats = processor.get_token_statistics([])
        
        assert stats['total_tokens'] == 0
        assert stats['valid_tokens'] == 0
        assert stats['avg_length'] == 0.0
        assert stats['length_distribution'] == {}
    
    def test_min_word_length_parameter(self):
        """Тест параметра минимальной длины слова."""
        processor = TokenProcessor(min_length=5)
        text = "Hola mundo español"
        tokens = processor.tokenize(text)
        
        # Только слова длиной 5+ символов
        assert "mundo" in tokens
        assert "español" in tokens
        assert "hola" not in tokens  # 4 символа
    
    def test_case_sensitivity(self):
        """Тест чувствительности к регистру."""
        processor = TokenProcessor()
        text = "HOLA Mundo ESPAÑOL"
        tokens = processor.tokenize(text)
        
        # Все токены должны быть в нижнем регистре
        assert all(token.islower() for token in tokens)
        assert "hola" in tokens
        assert "mundo" in tokens
        assert "español" in tokens
