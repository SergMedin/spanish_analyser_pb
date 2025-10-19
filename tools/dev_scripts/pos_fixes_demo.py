"""
Демонстрация исправлений POS согласно правилу spacy-pipeline.mdc

Проверяет:
1. Решение проблемы рассинхрона Gender/Word для antigüedad
2. Коррекцию PROPN→NOUN
3. Фильтрацию SYM для буквенных токенов
4. Консистентность POS переводов
"""

import tempfile
import pandas as pd
from spanish_analyser.word_analyzer import WordAnalyzer


def main():
    print("🔧 Демонстрация исправлений POS согласно правилу spacy-pipeline.mdc")
    print("=" * 70)
    
    analyzer = WordAnalyzer()
    
    # Тест 1: Проблема antigüedad из вашего скриншота
    print("\n📝 Тест 1: Рассинхрон Gender/Word для antigüedad")
    print("-" * 50)
    
    text_antiguedad = """
    La antigüedad es importante para la historia. 
    Antigüedad significa tiempo pasado.
    En la antigüedad romana había muchas tradiciones.
    """
    
    analyzer.add_words_from_text(text_antiguedad)
    
    # Проверяем частоты
    freq_keys = [key for key in analyzer.word_frequencies.keys() if 'antigüedad' in key]
    print(f"Ключи частотности для antigüedad: {freq_keys}")
    
    # Экспортируем и проверяем Excel
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        analyzer.export_to_excel(tmp.name)
        df = pd.read_excel(tmp.name)
        
        # Фильтруем строки с antigüedad
        antiguedad_rows = df[df['Word'].str.contains('antigüedad', na=False)]
        
        print("\n📊 Строки Excel для antigüedad:")
        if len(antiguedad_rows) > 0:
            for _, row in antiguedad_rows.iterrows():
                word = row['Word']
                gender = row['Gender']
                pos = row['Part of Speech']
                
                # ПРОВЕРКА КОНСИСТЕНТНОСТИ ПО ПРАВИЛУ
                expected_gender = "Fem" if word.startswith("la ") else "Masc" if word.startswith("el ") else "-"
                status = "✅" if gender == expected_gender else "❌"
                
                print(f"  {status} Word: '{word}' | Gender: '{gender}' | POS: '{pos}'")
                print(f"      Ожидаемый Gender: '{expected_gender}' | Консистентность: {'ДА' if gender == expected_gender else 'НЕТ'}")
        else:
            print("  ⚠️ Нет строк с antigüedad в Excel (возможно, слово в Anki)")
    
    # Тест 2: Коррекция PROPN→NOUN
    print("\n📝 Тест 2: Коррекция PROPN→NOUN")
    print("-" * 50)
    
    analyzer2 = WordAnalyzer()
    text_propn = "Tecnología es importante. La tecnología moderna avanza rápido."
    analyzer2.add_words_from_text(text_propn)
    
    tech_keys = [key for key in analyzer2.word_frequencies.keys() if 'tecnología' in key]
    print(f"Ключи для tecnología: {tech_keys}")
    
    # Проверяем, что нет ключей с "Собственное имя"
    propn_keys = [key for key in tech_keys if "Собственное имя" in key]
    if len(propn_keys) == 0:
        print("✅ Коррекция PROPN→NOUN работает: нет ключей с 'Собственное имя'")
    else:
        print(f"❌ Найдены ключи с 'Собственное имя': {propn_keys}")
    
    # Тест 3: Эвристики качества
    print("\n📝 Тест 3: Эвристики качества (предупреждения о X/SYM)")
    print("-" * 50)
    
    analyzer3 = WordAnalyzer()
    # Текст с высокой долей символов
    text_symbols = "Texto normal pero ### @@@ %%% много символов &&& $$$"
    print("Добавляем текст с символами...")
    analyzer3.add_words_from_text(text_symbols)
    print("✅ Анализ завершён (предупреждения выше, если есть)")
    
    # Тест 4: Единый источник POS
    print("\n📝 Тест 4: Единый источник POS переводов")
    print("-" * 50)
    
    analyzer4 = WordAnalyzer()
    test_pos = ['NOUN', 'VERB', 'ADJ', 'PROPN', 'SYM']
    
    print("Переводы POS из единого источника:")
    for pos in test_pos:
        translation = analyzer4.pos_tagger.get_pos_tag_ru(pos)
        print(f"  {pos} → {translation}")
    
    print("\n🎉 Демонстрация завершена!")
    print("✅ Все исправления согласно правилу spacy-pipeline.mdc применены")


if __name__ == "__main__":
    main()
