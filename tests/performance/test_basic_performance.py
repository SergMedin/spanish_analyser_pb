import time

import pytest

from spanish_analyser.word_analyzer import WordAnalyzer


@pytest.mark.performance
def test_add_words_basic_performance(sample_texts):
    """Проверяет, что базовый анализ работает достаточно быстро на простом тексте."""
    analyzer = WordAnalyzer()
    text = sample_texts["simple"] * 200  # Увеличим объём текста

    start = time.perf_counter()
    analyzer.add_words_from_text(text)
    duration = time.perf_counter() - start

    # Базовый грубый порог, чтобы ловить регрессии
    assert duration < 2.0, f"Слишком медленно: {duration:.3f}s"
