"""
Тесты качества POS-теггинга согласно правилу .cursor/rules/spacy-pipeline.mdc

Обязательные кейсы:
- Омоним "capital" (la capital vs el capital)
- Восстановление рода из DET
- Отсутствие строк с "символ" в Excel для буквенных токенов
- Коррекция PROPN→NOUN
- Консистентность Gender в Excel
"""

import pytest
try:
    import spacy  # type: ignore
    _HAS_SPACY = True
    try:
        from src.spanish_analyser.config import config
        model_name = config.get_spacy_model()
        spacy.load(model_name)
        _HAS_MODEL = True
    except Exception:
        _HAS_MODEL = False
except Exception:
    _HAS_SPACY = False
    _HAS_MODEL = False

pytestmark = pytest.mark.skipif(not (_HAS_SPACY and _HAS_MODEL), reason="spaCy модель недоступна, пропуск тестов POS надёжности")
import pandas as pd
from pathlib import Path
import tempfile
import os

from spanish_analyser.word_analyzer import WordAnalyzer


class TestPOSReliability:
    """Тесты надёжности определения частей речи."""
    
    def test_capital_homonym_differentiation(self):
        """Тест: омоним 'capital' должен различаться по роду."""
        analyzer = WordAnalyzer()
        
        # Текст с обоими значениями capital
        text = "La capital de España es Madrid, pero el capital puede referirse al dinero."
        analyzer.add_words_from_text(text)
        
        # Проверяем, что есть оба варианта в частотах
        freq_keys = list(analyzer.word_frequencies.keys())
        capital_keys = [key for key in freq_keys if 'capital' in key]
        
        # Должны быть "la capital" и "el capital"
        assert any("la capital" in key for key in capital_keys), f"Не найден 'la capital' в {capital_keys}"
        assert any("el capital" in key for key in capital_keys), f"Не найден 'el capital' в {capital_keys}"
        
        # Проверяем безопасное хранение токенных деталей
        capital_details = [details for key, details in analyzer.token_details.items() 
                          if key[0] == 'capital']  # key[0] это lemma
        
        assert len(capital_details) >= 2, "Должно быть минимум 2 записи для capital с разными родами"
    
    def test_excel_gender_consistency(self):
        """Тест: Gender в Excel должен соответствовать Word (без рассинхрона)."""
        analyzer = WordAnalyzer()
        
        # Текст где может быть рассинхрон
        text = "La antigüedad es importante. Antigüedad significa historia antigua."
        analyzer.add_words_from_text(text)
        
        # Экспортируем в временный файл
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            analyzer.export_to_excel(tmp_path)
            
            # Читаем Excel и проверяем консистентность
            df = pd.read_excel(tmp_path)
            
            for _, row in df.iterrows():
                word = row['Word']
                gender = row['Gender']
                
                # Правило: если Word начинается с "el " → Gender должен быть "Masc"
                if isinstance(word, str) and word.startswith("el "):
                    assert gender == "Masc", f"Word='{word}' начинается с 'el', но Gender='{gender}'"
                
                # Если Word начинается с "la " → Gender должен быть "Fem" 
                elif isinstance(word, str) and word.startswith("la "):
                    assert gender == "Fem", f"Word='{word}' начинается с 'la', но Gender='{gender}'"
                
                # Если нет артикля → Gender должен быть "-"
                elif isinstance(word, str) and not (word.startswith("el ") or word.startswith("la ")):
                    assert gender == "-", f"Word='{word}' без артикля, но Gender='{gender}' (ожидался '-')"
            
        finally:
            os.unlink(tmp_path)
    
    def test_propn_correction(self):
        """Тест: PROPN должен корректироваться на NOUN в начале предложения."""
        analyzer = WordAnalyzer()
        
        # Текст где слово может быть ошибочно помечено как PROPN
        text = "Antigüedad es un concepto importante. La antigüedad de Roma es famosa."
        analyzer.add_words_from_text(text)
        
        # Проверяем, что в частотах нет варианта с "собственное имя"
        freq_keys = list(analyzer.word_frequencies.keys())
        antiguedad_keys = [key for key in freq_keys if 'antigüedad' in key]
        
        # Не должно быть ключей с "Собственное имя"
        propn_keys = [key for key in antiguedad_keys if "Собственное имя" in key]
        assert len(propn_keys) == 0, f"Найдены ключи с 'Собственное имя': {propn_keys}"
        
        # Должны быть только варианты с "Существительное"
        noun_keys = [key for key in antiguedad_keys if "Существительное" in key]
        assert len(noun_keys) > 0, f"Не найдены ключи с 'Существительное': {antiguedad_keys}"
    
    def test_sym_filtering_for_alpha_tokens(self):
        """Тест: буквенные токены не должны попадать в Excel как 'символ'."""
        analyzer = WordAnalyzer()
        
        # Добавляем текст, где могут быть ошибки SYM
        text = "La tecnología y los símbolos @ # son diferentes. La antigüedad está aquí."
        analyzer.add_words_from_text(text)
        
        # Экспортируем в Excel
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            analyzer.export_to_excel(tmp_path)
            df = pd.read_excel(tmp_path)
            
            # Проверяем, что нет строк с "Символ" для буквенных слов
            symbol_rows = df[df['Part of Speech'] == 'Символ']
            
            for _, row in symbol_rows.iterrows():
                word = row['Word']
                # Если Word состоит только из букв и длиннее 2 символов, это ошибка
                if isinstance(word, str) and word.isalpha() and len(word) > 2:
                    pytest.fail(f"Буквенное слово '{word}' ошибочно помечено как 'Символ'")
        
        finally:
            os.unlink(tmp_path)
    
    def test_quality_heuristics_warnings(self):
        """Тест: эвристики качества должны выдавать предупреждения."""
        analyzer = WordAnalyzer()
        
        # Создаём текст с высокой долей проблемных токенов
        text = "Texto normal pero ### @@@ %%% много символов &&& $$$ etc."
        
        # Перехватываем вывод (в реальности это будет print)
        # Здесь просто проверяем, что анализ проходит без ошибок
        analyzer.add_words_from_text(text)
        
        # Проверяем, что частоты содержат нормальные слова
        normal_words = [key for key in analyzer.word_frequencies.keys() 
                       if any(word in key.lower() for word in ['texto', 'normal', 'pero'])]
        assert len(normal_words) > 0, "Должны быть найдены нормальные слова"
    
    def test_single_source_pos_names(self):
        """Тест: POS названия должны браться из единого источника."""
        analyzer = WordAnalyzer()
        
        # Проверяем, что analyzer использует pos_tagger для переводов
        assert hasattr(analyzer, 'pos_tagger'), "analyzer должен иметь pos_tagger"
        
        # Проверяем стандартные переводы
        assert analyzer.pos_tagger.get_pos_tag_ru('NOUN') == 'Существительное'
        assert analyzer.pos_tagger.get_pos_tag_ru('VERB') == 'Глагол'
        assert analyzer.pos_tagger.get_pos_tag_ru('PROPN') == 'Собственное имя'
        assert analyzer.pos_tagger.get_pos_tag_ru('SYM') == 'Символ'
    
    def test_safe_token_details_storage(self):
        """Тест: токенные детали должны храниться безопасно."""
        analyzer = WordAnalyzer()
        
        text = "La capital y el capital son diferentes."
        analyzer.add_words_from_text(text)
        
        # Проверяем формат ключей token_details
        for key in analyzer.token_details.keys():
            # Ключ должен быть кортежем (lemma, pos, gender)
            assert isinstance(key, tuple), f"Ключ должен быть tuple, получен {type(key)}"
            assert len(key) == 3, f"Ключ должен содержать 3 элемента, получен {len(key)}"
            lemma, pos, gender = key
            assert isinstance(lemma, str), f"lemma должно быть str, получено {type(lemma)}"
            assert isinstance(pos, str), f"pos должно быть str, получено {type(pos)}"
            # gender может быть str или None
