"""
Демо-скрипт для тестирования нового WordAnalyzer с разделением на компоненты.

Проверяет работу всех компонентов и их интеграцию.
"""

import os
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from spanish_analyser.word_analyzer import WordAnalyzer


def main():
    """Основная функция демо."""
    print("🔍 Демо нового WordAnalyzer с компонентами")
    print("=" * 50)
    
    try:
        # Создаём анализатор
        print("📝 Создаю WordAnalyzer...")
        analyzer = WordAnalyzer(
            min_word_length=3,
            spacy_model="es_core_news_md",
            output_dir="data/results"
        )
        
        print("✅ WordAnalyzer создан успешно!")
        
        # Тестовый текст
        test_text = """
        Hola mundo español. El niño está aquí con la niña.
        Tengo 5 manzanas y 3 peras. ¿Cómo estás?
        """
        
        print(f"\n📖 Анализирую текст:")
        print(f"'{test_text.strip()}'")
        
        # Анализируем текст
        print("\n🔍 Начинаю анализ...")
        result = analyzer.analyze_text(test_text)
        
        # Выводим результаты
        print(f"\n📊 Результаты анализа:")
        print(f"  Общее количество слов: {result.total_words}")
        print(f"  Уникальных слов: {result.unique_words}")
        print(f"  Неизвестных слов: {len(result.unknown_words)}")
        print(f"  Время обработки: {result.processing_time:.2f} сек")
        
        # Показываем слова для изучения
        print(f"\n📚 Слова для изучения:")
        unknown_words = analyzer.get_unknown_words_for_learning(result)
        for i, word_info in enumerate(unknown_words[:10], 1):
            print(f"  {i:2d}. {word_info.word:<15} ({word_info.pos_tag_ru:<12}) Частота: {word_info.frequency}")
        
        # Статистика компонентов
        print(f"\n📈 Статистика компонентов:")
        stats = analyzer.get_statistics()
        print(f"  Токенизатор: {stats['tokenizer']['valid_tokens']} валидных токенов")
        print(f"  Лемматизатор: кэш {stats['lemmatizer']['cache_size']} слов")
        print(f"  POS-теггер: модель {stats['pos_tagger']['model_name']} загружена: {stats['pos_tagger']['model_loaded']}")
        print(f"  Частотность: {stats['frequency_analyzer']['total_words']} слов")
        print(f"  Сравнение: {stats['word_comparator']['known_words_count']} известных слов")
        print(f"  Нормализатор: кэш {stats['word_normalizer']['cache_size']} слов")
        
        # Тестируем экспорт
        print(f"\n💾 Тестирую экспорт...")
        exported_files = analyzer.export_results(result, "demo_analysis")
        
        print(f"✅ Экспортировано {len(exported_files)} файлов:")
        for format_name, file_path in exported_files.items():
            print(f"  {format_name}: {file_path}")
        
        print(f"\n🎉 Демо завершено успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка в демо: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
