#!/usr/bin/env python3
"""
Прямой тест WordAnalyzer без импорта через __init__.py
"""

import sys
import os
import tempfile

# Добавляем путь к src
sys.path.append('src')

# Создаем временный файл с текстом для тестирования
test_text = """La casa es muy grande. Yo corro rápido en el parque.
Este libro es interesante. El niño come frutas todos los días.
"""

def test_word_analyzer_direct():
    """Тестирует WordAnalyzer напрямую"""
    print("🧪 Прямое тестирование WordAnalyzer")
    print("=" * 50)

    try:
        # Импортируем модули по отдельности, избегая __init__.py
        import importlib.util

        # Загружаем config.py
        config_path = 'src/spanish_analyser/config.py'
        spec = importlib.util.spec_from_file_location("config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        sys.modules["config"] = config_module
        spec.loader.exec_module(config_module)
        config = config_module.config

        # Загружаем word_analyzer.py
        word_analyzer_path = 'src/spanish_analyser/word_analyzer.py'
        spec = importlib.util.spec_from_file_location("word_analyzer", word_analyzer_path)
        word_analyzer_module = importlib.util.module_from_spec(spec)
        sys.modules["word_analyzer"] = word_analyzer_module
        spec.loader.exec_module(word_analyzer_module)

        WordAnalyzer = word_analyzer_module.WordAnalyzer

        analyzer = WordAnalyzer()

        print(f"spaCy модель загружена: {analyzer.nlp is not None}")
        print(f"Модель: {config.get_spacy_model()}")
        print()

        # Тестируем определение частей речи
        test_words = ["casa", "correr", "rápido", "en", "muy", "grande"]
        print("📝 Тестирование определения частей речи:")
        print("-" * 40)

        for word in test_words:
            pos = analyzer.determine_pos(word)
            print("12")

        print()

        # Тестируем анализ текста
        print("📊 Тестирование анализа текста:")
        print("-" * 40)

        analyzer.add_words_from_text(test_text)

        print("Результаты анализа:")
        for word_with_pos, freq in analyzer.word_frequencies.most_common(10):
            if ' (' in word_with_pos and word_with_pos.endswith(')'):
                word = word_with_pos.split(' (')[0]
                pos = word_with_pos.split(' (')[1].rstrip(')')
            else:
                word = word_with_pos
                pos = 'неизвестно'
            print(f"  {word}: {pos} ({freq})")

        print()

        # Тестируем экспорт в Excel (создаем временный файл)
        print("📈 Тестирование экспорта в Excel:")
        print("-" * 40)

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            temp_filename = tmp_file.name

        try:
            analyzer.export_to_excel(temp_filename)
            print(f"✅ Excel файл создан: {temp_filename}")

            # Проверяем содержимое
            import pandas as pd
            df = pd.read_excel(temp_filename)
            print(f"✅ В Excel файле {len(df)} строк")

            if len(df) > 0:
                print("📋 Пример данных из Excel:")
                for i, row in df.head(3).iterrows():
                    print(f"  {row['Word']}: {row['Part of Speech']}")

        except Exception as e:
            print(f"❌ Ошибка при экспорте: {e}")
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
                print(f"🗑️ Временный файл удален: {temp_filename}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_word_analyzer_direct()


