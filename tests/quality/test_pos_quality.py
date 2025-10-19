import pytest

from spanish_analyser.word_analyzer import WordAnalyzer
from spanish_analyser.text_processor import SpanishTextProcessor


@pytest.mark.quality
def test_pos_tagging_quality(test_config):
    """Проверяет минимальную точность POS-тегов на небольшом эталоне.

    Тест пропускается, если модель spaCy недоступна.
    """
    # Если нет spaCy модели — пропускаем тест качества
    try:
        import spacy
        from src.spanish_analyser.config import config
        model_name = config.get_spacy_model()
        try:
            spacy.load(model_name)
        except Exception:
            pytest.skip(f"spaCy модель {model_name} недоступна, пропуск теста качества POS")
    except Exception:
        pytest.skip("spaCy недоступен, пропуск теста качества POS")

    analyzer = WordAnalyzer()
    processor = SpanishTextProcessor()

    # Используем цельное предложение, оцениваем POS по леммам для устойчивости
    sentence = "Los gatos corren rápido y la casa es bonita."
    gold = {
        "gato": "существительное",
        "correr": "глагол",
        "rápido": "наречие",
        "bonito": "прилагательное",
        "casa": "существительное",
    }

    # Добавим текст в анализатор, чтобы он применил лемматизацию
    analyzer.add_words_from_text(sentence)

    correct = 0
    total = 0
    for lemma, expected_pos in gold.items():
        total += 1
        predicted = analyzer.word_pos_tags.get(lemma) or analyzer.determine_pos(lemma)
        if predicted == expected_pos:
            correct += 1

    accuracy = correct / max(1, total)
    min_acc = float(test_config.get("quality", {}).get("min_pos_accuracy", 0.7))
    assert accuracy >= min_acc, f"Точность POS {accuracy:.2f} ниже порога {min_acc:.2f}"


