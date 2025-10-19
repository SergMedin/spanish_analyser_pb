"""
Тесты для компонента WordNormalizer.
"""

import pytest

from src.spanish_analyser.components.normalizer import WordNormalizer


class TestWordNormalizer:
    """Тесты для WordNormalizer."""
    
    def test_init(self):
        """Тест инициализации."""
        normalizer = WordNormalizer()
        assert normalizer.use_cache is True
        assert len(normalizer._cache) == 0
        
        normalizer = WordNormalizer(use_cache=False)
        assert normalizer.use_cache is False
    
    def test_normalize_basic(self):
        """Тест базовой нормализации."""
        normalizer = WordNormalizer()
        
        # Приведение к нижнему регистру
        assert normalizer.normalize("HOLA") == "hola"
        assert normalizer.normalize("Mundo") == "mundo"
        # Сохранение диакритики при использовании лемматизации spaCy
        assert normalizer.normalize("ESPAÑOL") == "español"
    
    def test_normalize_accents(self):
        """Тест нормализации акцентов."""
        normalizer = WordNormalizer()
        
        # Отдельные символы с диакритикой сохраняются
        assert normalizer.normalize("á") == "á"
        assert normalizer.normalize("é") == "é"
        assert normalizer.normalize("í") == "í"
        assert normalizer.normalize("ó") == "ó"
        assert normalizer.normalize("ú") == "ú"
        assert normalizer.normalize("ñ") == "ñ"
        assert normalizer.normalize("ü") == "ü"
        
        # Слова с диакритикой и лемматизацией
        assert normalizer.normalize("niño") == "niño"
        # Может быть как estar (с реальной моделью), так и está (со стабом)
        assert normalizer.normalize("está") in ["estar", "está"]
        assert normalizer.normalize("aquí") == "aquí"
        assert normalizer.normalize("niña") == "niña"
    
    def test_normalize_whitespace(self):
        """Тест нормализации пробелов."""
        normalizer = WordNormalizer()
        
        assert normalizer.normalize("  hola  ") == "hola"
        assert normalizer.normalize("\t\tmundo\n") == "mundo"
        assert normalizer.normalize("  español  ") == "español"
    
    def test_normalize_empty(self):
        """Тест нормализации пустых значений."""
        normalizer = WordNormalizer()
        
        assert normalizer.normalize("") == ""
        assert normalizer.normalize(None) == ""
        assert normalizer.normalize("   ") == ""
    
    def test_normalize_batch(self):
        """Тест батчевой нормализации."""
        normalizer = WordNormalizer()
        
        words = ["HOLA", "Mundo", "ESPAÑOL", "niño", "está"]
        normalized = normalizer.normalize_batch(words)
        
        # Проверяем что первые 4 элемента точно соответствуют ожиданиям
        assert normalized[:4] == ["hola", "mundo", "español", "niño"]
        # Для está может быть как estar, так и está в зависимости от доступности модели
        assert normalized[4] in ["estar", "está"]
    
    def test_normalize_batch_empty(self):
        """Тест батчевой нормализации пустого списка."""
        normalizer = WordNormalizer()
        
        assert normalizer.normalize_batch([]) == []
        assert normalizer.normalize_batch(None) == []
    
    def test_cache_functionality(self):
        """Тест функциональности кэша."""
        normalizer = WordNormalizer(use_cache=True)
        
        # Первый вызов - добавляет в кэш
        result1 = normalizer.normalize("HOLA")
        assert result1 == "hola"
        assert "HOLA" in normalizer._cache
        assert normalizer._cache["HOLA"] == "hola"
        
        # Второй вызов - использует кэш
        result2 = normalizer.normalize("HOLA")
        assert result2 == "hola"
        assert result1 == result2
    
    def test_cache_disabled(self):
        """Тест отключённого кэша."""
        normalizer = WordNormalizer(use_cache=False)
        
        normalizer.normalize("HOLA")
        assert len(normalizer._cache) == 0
    
    def test_clear_cache(self):
        """Тест очистки кэша."""
        normalizer = WordNormalizer(use_cache=True)
        
        # Добавляем несколько слов в кэш
        normalizer.normalize("HOLA")
        normalizer.normalize("MUNDO")
        assert len(normalizer._cache) == 2
        
        # Очищаем кэш
        normalizer.clear_cache()
        assert len(normalizer._cache) == 0
    
    def test_get_cache_stats(self):
        """Тест получения статистики кэша."""
        normalizer = WordNormalizer(use_cache=True)
        
        stats = normalizer.get_cache_stats()
        assert stats['cache_size'] == 0
        
        # Добавляем слова в кэш
        normalizer.normalize("HOLA")
        normalizer.normalize("MUNDO")
        
        stats = normalizer.get_cache_stats()
        assert stats['cache_size'] == 2
    
    def test_is_spanish_word(self):
        """Тест проверки испанских слов."""
        normalizer = WordNormalizer()
        
        # Слова с испанскими символами
        assert normalizer.is_spanish_word("niño") is True
        assert normalizer.is_spanish_word("está") is True
        assert normalizer.is_spanish_word("aquí") is True
        assert normalizer.is_spanish_word("niña") is True
        
        # Слова без испанских символов
        assert normalizer.is_spanish_word("hola") is False
        assert normalizer.is_spanish_word("mundo") is False
        assert normalizer.is_spanish_word("español") is True  # ñ считается испанским символом
        
        # Пустые значения
        assert normalizer.is_spanish_word("") is False
        assert normalizer.is_spanish_word(None) is False
    
    def test_get_spanish_character_count(self):
        """Тест подсчёта испанских символов."""
        normalizer = WordNormalizer()
        
        assert normalizer.get_spanish_character_count("niño") == 1  # ñ
        assert normalizer.get_spanish_character_count("está") == 1  # á
        assert normalizer.get_spanish_character_count("aquí") == 1  # í
        assert normalizer.get_spanish_character_count("niña") == 1  # ñ
        
        # Слова без испанских символов
        assert normalizer.get_spanish_character_count("hola") == 0
        assert normalizer.get_spanish_character_count("mundo") == 0
        
        # Пустые значения
        assert normalizer.get_spanish_character_count("") == 0
        assert normalizer.get_spanish_character_count(None) == 0
    
    def test_unicode_normalization(self):
        """Тест Unicode нормализации."""
        normalizer = WordNormalizer()
        
        # Проверяем, что диакритические знаки корректно обрабатываются
        # Это может зависеть от версии Python и системы
        result = normalizer.normalize("café")
        # При лемматизации spaCy диакритика сохраняется
        assert "é" in result
    
    def test_mixed_content(self):
        """Тест нормализации смешанного контента."""
        normalizer = WordNormalizer()
        
        # Смесь букв, цифр, символов
        assert normalizer.normalize("HOLA123!@#") == "hola123!@#"
        # Может быть как niño (с реальной моделью), так и niño-2024 (со стабом)  
        assert normalizer.normalize("niño-2024") in ["niño", "niño-2024"]
        
        # Специальные случаи: леммы с сохранением диакритики
        assert normalizer.normalize("está...") in ["estar", "está", "está..."]
        assert normalizer.normalize("¿qué?") in ["qué", "¿qué?"]
