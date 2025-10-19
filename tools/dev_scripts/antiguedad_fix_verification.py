"""
Проверка исправлений для проблемы "antigüedad".

Демонстрирует решение всех проблем, выявленных пользователем:
1. Консолидация существительных с/без артикля
2. Коррекция PROPN→NOUN для "Antigüedad" в начале предложения
3. Единый источник POS переводов
4. Правильное определение Gender из Word колонки
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.spanish_analyser.word_analyzer import WordAnalyzer
from src.spanish_analyser.components.spacy_manager import SpacyManager
from src.spanish_analyser.components.pos_tagger import POSTagger


def test_antiguedad_fixes():
    """Тестируем исправления на примере antigüedad."""
    
    print("🔧 Тестирование исправлений для 'antigüedad'")
    print("=" * 60)
    
    # Тестовый текст с различными контекстами
    test_text = """
    Antigüedad es un concepto importante en arqueología. 
    La antigüedad del objeto fue determinada por carbono-14.
    El estudio de la antigüedad clásica es fascinante.
    Las antigüedades se venden en este mercado.
    """
    
    print(f"📝 Тестовый текст:\n{test_text.strip()}\n")
    
    # Тест 1: Проверка централизованного менеджера spaCy
    print("🔍 Тест 1: SpacyManager с коррекциями POS")
    spacy_manager = SpacyManager()
    doc = spacy_manager.analyze_text_with_corrections(test_text)
    
    print("Анализ токенов с коррекциями:")
    for token in doc:
        if token.is_alpha and len(token.text) >= 3:
            print(f"  {token.text} -> {token.pos_} (лемма: {token.lemma_})")
    
    # Тест 2: Единый источник POS переводов
    print(f"\n🗣️ Тест 2: Единый источник POS переводов")
    pos_tagger = POSTagger()
    print("Переводы основных POS:")
    for pos in ['NOUN', 'PROPN', 'ADJ', 'VERB', 'SYM']:
        print(f"  {pos} -> {pos_tagger.get_pos_tag_ru(pos)}")
    
    # Тест 3: WordAnalyzer с новой логикой
    print(f"\n📊 Тест 3: WordAnalyzer с консолидацией")
    analyzer = WordAnalyzer()
    analyzer.add_words_from_text(test_text)
    
    print("Частоты слов до экспорта:")
    for word_pos, freq in analyzer.word_frequencies.most_common():
        if 'antigüedad' in word_pos.lower():
            print(f"  {word_pos}: {freq}")
    
    # Тест 4: Проверка консолидации в экспорте
    print(f"\n🗂️ Тест 4: Симуляция экспорта с консолидацией")
    
    # Создаём временный Excel файл для проверки
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        analyzer.export_to_excel(tmp_file.name)
        
        # Читаем результат
        import pandas as pd
        df = pd.read_excel(tmp_file.name)
        
        # Фильтруем строки с antigüedad
        antiguedad_rows = df[df['Lemma'].str.contains('antigüedad', case=False, na=False)]
        
        print("Строки с 'antigüedad' в Excel:")
        if not antiguedad_rows.empty:
            for _, row in antiguedad_rows.iterrows():
                print(f"  Word: '{row['Word']}' | POS: '{row['Part of Speech']}' | Gender: '{row['Gender']}' | Count: {row['Count']}")
        else:
            print("  ❌ Не найдено строк с 'antigüedad'")
        
        # Очистка
        os.unlink(tmp_file.name)
    
    # Тест 5: Проверка качественных метрик
    print(f"\n📈 Тест 5: Качественные метрики")
    quality_stats = spacy_manager.get_quality_statistics(doc)
    
    print(f"Статистика качества:")
    print(f"  Всего alpha токенов: {quality_stats['total_alpha_tokens']}")
    print(f"  X/SYM токенов: {quality_stats['x_sym_tokens']} ({quality_stats['x_sym_ratio']:.1%})")
    print(f"  Доля основных POS: {quality_stats['main_pos_ratio']:.1%}")
    
    if quality_stats['quality_warnings']:
        print("Предупреждения качества:")
        for warning in quality_stats['quality_warnings']:
            print(f"  {warning}")
    else:
        print("  ✅ Предупреждений качества нет")
    
    print("\n" + "=" * 60)
    print("✅ Все тесты исправлений завершены!")
    print("💡 Ожидаемые результаты:")
    print("  - 'Antigüedad' должно быть распознано как NOUN, а не PROPN")
    print("  - Варианты 'antigüedad' и 'la antigüedad' должны быть консолидированы")
    print("  - Gender должен соответствовать артиклю в Word колонке")
    print("  - Все POS переводы должны быть единообразными")


def test_specific_consolidation_logic():
    """Тестируем логику консолидации на конкретном примере."""
    print(f"\n🧪 Дополнительный тест: логика консолидации")
    print("-" * 40)
    
    # Создаём тестовые частоты как если бы они пришли из word_frequencies
    test_frequencies = {
        'antigüedad (Существительное)': 2,      # без артикля
        'la antigüedad (Существительное)': 11,  # с артиклем Fem
        'capital (Прилагательное)': 5,          # не существительное - не трогаем
    }
    
    print("Исходные частоты:")
    for word_pos, freq in test_frequencies.items():
        print(f"  {word_pos}: {freq}")
    
    # Симулируем логику консолидации из export_to_excel
    lemma_variants = {}
    non_nouns = {}
    
    for word_with_pos, freq in test_frequencies.items():
        if ' (' in word_with_pos and word_with_pos.endswith(')'):
            word_part = word_with_pos.split(' (')[0]
            pos_tag = word_with_pos.split(' (')[1].rstrip(')')
        else:
            continue
        
        # Определяем базовую лемму
        if word_part.startswith(('el ', 'la ')):
            base_lemma = word_part.split(' ', 1)[1]
            has_article = True
        else:
            base_lemma = word_part
            has_article = False
        
        if pos_tag == 'Существительное':
            if base_lemma not in lemma_variants:
                lemma_variants[base_lemma] = {'with_article': {}, 'without_article': {}}
            
            if has_article:
                lemma_variants[base_lemma]['with_article'][word_with_pos] = freq
            else:
                lemma_variants[base_lemma]['without_article'][word_with_pos] = freq
        else:
            non_nouns[word_with_pos] = freq
    
    print(f"\nАнализ вариантов существительных:")
    for base_lemma, variants in lemma_variants.items():
        print(f"  Лемма '{base_lemma}':")
        print(f"    С артиклем: {variants['with_article']}")
        print(f"    Без артикля: {variants['without_article']}")
    
    # Консолидируем
    consolidated_frequencies = {}
    
    for base_lemma, variants in lemma_variants.items():
        with_article = variants['with_article']
        without_article = variants['without_article']
        
        if with_article:
            # Есть варианты с артиклем - используем их
            for freq_key, freq in with_article.items():
                consolidated_frequencies[freq_key] = freq
            
            # Добавляем частоты вариантов без артикля к вариантам с артиклем  
            for freq_key_without, freq_without in without_article.items():
                for freq_key_with in with_article.keys():
                    word_with = freq_key_with.split(' (')[0]
                    if word_with.endswith(' ' + base_lemma):
                        consolidated_frequencies[freq_key_with] += freq_without
                        break
        else:
            # Только варианты без артикля
            for freq_key, freq in without_article.items():
                consolidated_frequencies[freq_key] = freq
    
    consolidated_frequencies.update(non_nouns)
    
    print(f"\nКонсолидированные частоты:")
    for word_pos, freq in consolidated_frequencies.items():
        print(f"  {word_pos}: {freq}")
        
        # Проверяем корректность Gender
        word_part = word_pos.split(' (')[0]
        if word_part.startswith("el "):
            expected_gender = "Masc"
        elif word_part.startswith("la "):
            expected_gender = "Fem"
        else:
            expected_gender = "-"
        print(f"    -> Expected Gender: {expected_gender}")


if __name__ == "__main__":
    test_antiguedad_fixes()
    test_specific_consolidation_logic()
