import pytest

from spanish_analyser.word_analyzer import WordAnalyzer
from spanish_analyser.text_processor import SpanishTextProcessor


@pytest.mark.integration
def test_full_pipeline_html_to_excel(sample_texts, mock_anki, temp_directory):
    """Проверяет упрощённый пайплайн: HTML → текст → анализ → Excel.

    Тест не зависит от наличия реальной spaCy модели.
    """
    html_text = sample_texts["html"]

    # 1) Очистка HTML → текст
    processor = SpanishTextProcessor()
    clean_text = processor.clean_text(html_text, remove_prefixes=True)
    assert "<" not in clean_text and ">" not in clean_text

    # 2) Анализ слов
    analyzer = WordAnalyzer()
    analyzer.load_known_words_from_anki(mock_anki)
    analyzer.add_words_from_text(clean_text)

    # 3) Экспорт в Excel
    output_file = temp_directory / "analysis.xlsx"
    analyzer.export_to_excel(str(output_file))

    assert output_file.exists()
    assert output_file.stat().st_size > 0
