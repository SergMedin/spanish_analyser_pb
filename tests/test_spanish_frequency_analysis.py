"""
Тест частотного анализа на реалистичном испанском тексте

Задача теста:
- Сгенерировать репрезентативный испанский текст с разными формами слов и временами
- Прогнать анализатор без участия Anki
- Проверить, что частоты по леммам соответствуют ожидаемым значениям
- Убедиться, что применяется глобальный порог минимальной длины слова

Важно:
- Анализатор сохраняет частоты по ЛЕММАМ (spaCy), поэтому проверяем именно леммы
- Часть речи может варьироваться для разных моделей/версий, поэтому не фиксируем её строго
"""

import unittest
from pathlib import Path
import sys

# Добавляем путь к src, чтобы можно было импортировать пакет
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spanish_analyser.word_analyzer import WordAnalyzer


class TestSpanishFrequencyAnalysis(unittest.TestCase):
    """Интеграционный тест частотного анализа по испанскому тексту"""

    def setUp(self):
        # Инициализируем анализатор. В рамках этого теста НЕ загружаем известные слова из Anki.
        self.analyzer = WordAnalyzer()

    def _get_lemma_count(self, lemma: str) -> int:
        """
        Возвращает суммарную частоту по лемме (игнорируя часть речи в ключе и артикли).
        
        Важно: WordAnalyzer сохраняет существительные с артиклями (например, "la casa"),
        поэтому этот метод проверяет как точное совпадение леммы, так и с артиклями.
        """
        total = 0
        for word_with_pos, freq in self.analyzer.word_frequencies.items():
            # Извлекаем основное слово из ключа (убираем часть речи в скобках)
            word_part = word_with_pos.split(" (")[0]
            # Проверяем точное совпадение леммы или совпадение с учётом артикля
            if word_part == lemma or word_part == f"el {lemma}" or word_part == f"la {lemma}":
                total += freq
        return total

    def test_frequency_on_realistic_text(self):
        """Проверяем частоты по ключевым леммам и применение порога min_word_length."""
        # Реалистичный испанский текст с разными временами и формами:
        # - comer: como, comes, comió, comía, comeremos, (han) comido → 6 вхождений
        # - hablar: hablo, hablas, habló, hablaba, hablaremos, (han) hablado → 6 вхождений
        # - casa: casa, casas, casa, casas → 4 вхождения
        # - bonito: bonita, bonitas → 2 вхождения
        # - ser: es, son → 2 вхождения (лемма 'ser' длиной 3 должна проходить порог)
        # Остальные короткие служебные слова типа "y", "en", "la/las" должны отсечься по длине
        text = (
            "Yo como en la casa. "
            "Tú comes en las casas. "
            "Él comió ayer y comía antes. "
            "Nosotros comeremos mañana. "
            "Ellos han comido mucho. "
            "La casa es bonita. "
            "Las casas son bonitas. "
            "Hablo, hablas, habló, hablaba, hablaremos, han hablado."
        )

        # Запускаем анализ
        self.analyzer.add_words_from_text(text)

        # Проверим, что применён глобальный порог минимальной длины для всех лемм
        for word_with_pos in self.analyzer.word_frequencies.keys():
            lemma = word_with_pos.split(" (")[0]
            self.assertGreaterEqual(
                len(lemma),
                self.analyzer.min_word_length,
                msg=f"Лемма '{lemma}' короче порога {self.analyzer.min_word_length}"
            )

        # Проверим частоты по ключевым леммам.
        # Важно: модель spaCy может по-разному лемматизировать отдельные формы
        # (например, «como» как союз, а не форма «comer»; «él» может сливаться в токен «hab él» и т.п.).
        # Поэтому используем нижние границы для устойчивости к версиям модели.
        self.assertGreaterEqual(self._get_lemma_count("comer"), 4, "Ожидается не менее 4 вхождений леммы 'comer'")
        self.assertGreaterEqual(self._get_lemma_count("hablar"), 5, "Ожидается не менее 5 вхождений леммы 'hablar'")
        self.assertGreaterEqual(self._get_lemma_count("casa"), 4, "Ожидается не менее 4 вхождений леммы 'casa'")
        self.assertGreaterEqual(self._get_lemma_count("bonito"), 2, "Ожидается не менее 2 вхождений леммы 'bonito'")
        self.assertGreaterEqual(self._get_lemma_count("ser"), 2, "Ожидается не менее 2 вхождений леммы 'ser'")


if __name__ == "__main__":
    unittest.main()
