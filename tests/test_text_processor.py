"""
Тесты для модуля text_processor
"""

import unittest
from unittest.mock import patch
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spanish_analyser.text_processor import SpanishTextProcessor


class TestSpanishTextProcessor(unittest.TestCase):
    """Тесты для класса SpanishTextProcessor"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.processor = SpanishTextProcessor()
    
    def test_spanish_dominant_string(self):
        """Тест определения доминирующего языка"""
        # Тест с испанским текстом
        result = self.processor.get_spanish_dominant_string("hola mundo", "привет мир")
        self.assertEqual(result, "hola mundo")
        
        # Тест с русским текстом
        result = self.processor.get_spanish_dominant_string("привет мир", "hola mundo")
        self.assertEqual(result, "hola mundo")
        
        # Тест с равными значениями
        result = self.processor.get_spanish_dominant_string("hello", "world")
        self.assertEqual(result, "hello")  # По умолчанию возвращает первую строку
    
    def test_remove_spanish_prefixes(self):
        """Тест удаления испанских префиксов"""
        # Тест с артиклем "los"
        result = self.processor.remove_spanish_prefixes("Los colores")
        self.assertEqual(result, "colores")
        
        # Тест с артиклем "la"
        result = self.processor.remove_spanish_prefixes("La casa")
        self.assertEqual(result, "casa")
        
        # Тест без префикса
        result = self.processor.remove_spanish_prefixes("casa")
        self.assertEqual(result, "casa")
        
        # Тест с пустой строкой
        result = self.processor.remove_spanish_prefixes("")
        self.assertEqual(result, "")
    
    def test_remove_html_tags(self):
        """Тест удаления HTML тегов"""
        # Тест с простыми тегами
        result = self.processor.remove_html_tags("<p>Hola mundo</p>")
        self.assertEqual(result, "Hola mundo")
        
        # Тест с вложенными тегами
        result = self.processor.remove_html_tags("<div><span>Texto</span></div>")
        self.assertEqual(result, "Texto")
        
        # Тест без тегов
        result = self.processor.remove_html_tags("Texto simple")
        self.assertEqual(result, "Texto simple")
        
        # Тест с пустой строкой
        result = self.processor.remove_html_tags("")
        self.assertEqual(result, "")
    
    def test_clean_text(self):
        """Тест полной очистки текста"""
        # Тест с HTML и префиксами
        result = self.processor.clean_text("<p>Los colores</p>")
        self.assertEqual(result, "colores")
        
        # Тест без HTML, но с префиксами
        result = self.processor.clean_text("La casa")
        self.assertEqual(result, "casa")
        
        # Тест без очистки префиксов
        result = self.processor.clean_text("<p>Los colores</p>", remove_prefixes=False)
        self.assertEqual(result, "Los colores")
    
    def test_extract_spanish_words(self):
        """Тест извлечения испанских слов"""
        # Тест с испанским текстом
        result = self.processor.extract_spanish_words("Hola mundo, ¿cómo estás?")
        self.assertIn("hola", result)
        self.assertIn("mundo", result)
        self.assertIn("cómo", result)
        self.assertIn("estás", result)
        
        # Тест с пустой строкой
        result = self.processor.extract_spanish_words("")
        self.assertEqual(result, [])
        
        # Тест с короткими словами (должны быть отфильтрованы)
        result = self.processor.extract_spanish_words("a b c de")
        self.assertEqual(result, [])  # Все слова короче 3 символов


if __name__ == "__main__":
    unittest.main()
