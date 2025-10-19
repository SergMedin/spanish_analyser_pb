"""
Тесты для модуля word_analyzer
"""

import unittest
import tempfile
import os
import json
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spanish_analyser.word_analyzer import WordAnalyzer


class TestWordAnalyzer(unittest.TestCase):
    """Тесты для класса WordAnalyzer"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.analyzer = WordAnalyzer()
    
    def test_add_words_from_text(self):
        """Тест добавления слов из текста"""
        # Добавляем слова
        self.analyzer.add_words_from_text("hola mundo")
        
        # Проверяем, что слова добавлены в формате "слово (часть_речи)"
        # spaCy может определять части речи по-разному, поэтому проверяем наличие слов
        hola_found = any("hola (" in word for word in self.analyzer.word_frequencies.keys())
        mundo_found = any("mundo (" in word for word in self.analyzer.word_frequencies.keys())
        
        self.assertTrue(hola_found, f"Слово 'hola' не найдено в {list(self.analyzer.word_frequencies.keys())}")
        self.assertTrue(mundo_found, f"Слово 'mundo' не найдено в {list(self.analyzer.word_frequencies.keys())}")
        
        # Проверяем частоту
        hola_word = next(word for word in self.analyzer.word_frequencies.keys() if "hola (" in word)
        mundo_word = next(word for word in self.analyzer.word_frequencies.keys() if "mundo (" in word)
        
        self.assertEqual(self.analyzer.word_frequencies[hola_word], 1)
        self.assertEqual(self.analyzer.word_frequencies[mundo_word], 1)
        
        # Добавляем снова
        self.analyzer.add_words_from_text("hola mundo")
        self.assertEqual(self.analyzer.word_frequencies[hola_word], 2)
        self.assertEqual(self.analyzer.word_frequencies[mundo_word], 2)
    
    def test_categorize_words_by_frequency(self):
        """Тест категоризации слов по частоте"""
        # Добавляем слова с разной частотой
        self.analyzer.add_words_from_text("muyfrecuente " * 150)  # > 100
        self.analyzer.add_words_from_text("frecuente " * 75)       # 50-100
        self.analyzer.add_words_from_text("medio " * 35)           # 20-49
        self.analyzer.add_words_from_text("raro " * 10)            # 5-19
        self.analyzer.add_words_from_text("muyraro " * 3)         # 1-4
    
        categories = self.analyzer.categorize_words_by_frequency()
    
        # Проверяем, что слова находятся в правильных категориях
        # spaCy может определять части речи по-разному, поэтому проверяем наличие слов
        muyfrecuente_found = any("muyfrecuente (" in word for word in categories["очень_часто"])
        frecuente_found = any("frecuente (" in word for word in categories["часто"])
        medio_found = any("medio (" in word for word in categories["средне"])
        raro_found = any("raro (" in word for word in categories["редко"])
        muyraro_found = any("muyraro (" in word for word in categories["очень_редко"])
        
        self.assertTrue(muyfrecuente_found, f"Слово 'muyfrecuente' не найдено в очень_часто: {categories['очень_часто']}")
        self.assertTrue(frecuente_found, f"Слово 'frecuente' не найдено в часто: {categories['часто']}")
        self.assertTrue(medio_found, f"Слово 'medio' не найдено в средне: {categories['средне']}")
        self.assertTrue(raro_found, f"Слово 'raro' не найдено в редко: {categories['редко']}")
        self.assertTrue(muyraro_found, f"Слово 'muyraro' не найдено в очень_редко: {categories['очень_редко']}")
    
    def test_get_new_words(self):
        """Тест получения новых слов"""
        # Добавляем слова
        self.analyzer.add_words_from_text("nuevo conocido")
    
        # Добавляем известные слова
        self.analyzer.known_words.add("conocido")
    
        # Получаем новые слова
        new_words = self.analyzer.get_new_words(exclude_known=True)
        
        # Проверяем, что новое слово найдено в формате "слово (часть_речи)"
        self.assertIn("nuevo (Прилагательное)", new_words)
        # Проверяем, что известное слово не включено
        self.assertNotIn("conocido (Прилагательное)", new_words)
    
    def test_get_top_words(self):
        """Тест получения топ слов"""
        # Добавляем слова
        self.analyzer.add_words_from_text("primero segundo tercero")
        self.analyzer.add_words_from_text("primero segundo")
        self.analyzer.add_words_from_text("primero")
    
        # Получаем топ 2 слова
        top_words = self.analyzer.get_top_words(2)
        self.assertEqual(len(top_words), 2)
        
        # Проверяем, что самое частое слово на первом месте
        self.assertEqual(top_words[0][0], "primero (Прилагательное)")  # Самое частое
        self.assertEqual(top_words[0][1], 3)  # Частота = 3
    
    def test_load_known_words_from_file(self):
        """Тест загрузки известных слов из файла (устаревший метод)"""
        # Создаём временный файл
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write("hola\nmundo\ncasa\n")
            temp_file = f.name
        
        try:
            # Загружаем слова (устаревший метод)
            result = self.analyzer.load_known_words(temp_file)
            self.assertTrue(result)
            self.assertEqual(len(self.analyzer.known_words), 3)
            self.assertIn("hola", self.analyzer.known_words)
            self.assertIn("mundo", self.analyzer.known_words)
            self.assertIn("casa", self.analyzer.known_words)
        finally:
            # Удаляем временный файл
            os.unlink(temp_file)
    
    def test_load_known_words_from_anki(self):
        """Тест загрузки известных слов из Anki"""
        # Создаём мок для AnkiIntegration
        from unittest.mock import Mock
        
        mock_anki = Mock()
        mock_anki.is_connected.return_value = True
        mock_anki.find_notes_by_deck.return_value = [1, 2, 3]
        mock_anki.extract_text_from_notes.return_value = [
            {
                'texts': ['hola mundo', 'casa bonita'],
                'note_type': 'Basic',
                'tags': ['spanish']
            }
        ]
        
        # Загружаем слова из Anki
        result = self.analyzer.load_known_words_from_anki(mock_anki)
        self.assertTrue(result)
        self.assertGreater(len(self.analyzer.known_words), 0)
    

    
    
    def test_reset(self):
        """Тест сброса статистики"""
        # Добавляем слова
        self.analyzer.add_words_from_text("hola mundo")
        self.analyzer.known_words.add("test")
        
        # Проверяем, что слова добавлены
        self.assertGreater(len(self.analyzer.word_frequencies), 0)
        
        # Сбрасываем
        self.analyzer.reset()
        
        # Проверяем, что статистика сброшена
        self.assertEqual(len(self.analyzer.word_frequencies), 0)
        self.assertEqual(len(self.analyzer.word_categories), 0)


if __name__ == "__main__":
    unittest.main()
