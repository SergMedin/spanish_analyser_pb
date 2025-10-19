#!/usr/bin/env python3
"""
Основной скрипт Spanish Analyser

Простая точка входа для демонстрации возможностей проекта.
Для полного функционала используйте: python -m spanish_analyser.cli
"""

import os
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from spanish_analyser import SpanishTextProcessor, WordAnalyzer
from spanish_analyser.config import config


def demo_analysis():
    """Демонстрация основных возможностей анализа"""
    print("=== Демонстрация Spanish Analyser ===\n")
    
    # Инициализируем компоненты
    text_processor = SpanishTextProcessor()
    word_analyzer = WordAnalyzer()
    
    print("🔧 Инициализация компонентов...")
    
    # Демонстрируем обработку текста
    print("\n📝 Демонстрация обработки текста:")
    sample_texts = [
        "<p>Los colores del semáforo</p>",
        "El coche rojo se detiene",
        "Las señales de tráfico son importantes"
    ]
    
    for i, text in enumerate(sample_texts, 1):
        cleaned = text_processor.clean_text(text)
        print(f"{i}. Исходный: {text}")
        print(f"   Очищенный: {cleaned}")
    
    # Демонстрируем анализ слов
    print("\n📊 Анализ слов:")
    for text in sample_texts:
        cleaned = text_processor.clean_text(text)
        word_analyzer.add_words_from_text(cleaned)
    
    # Показываем статистику
    stats = word_analyzer.get_summary_stats()
    print(f"✨ Всего уникальных слов: {stats['всего_уникальных_слов']}")
    print(f"📈 Новых слов: {stats['новых_слов']}")
    
    # Показываем топ слов
    top_words = word_analyzer.get_top_words(5)
    print(f"\n🏆 Топ 5 слов:")
    for word, freq in top_words:
        print(f"   • {word}: {freq}")
    
    # Проверяем интеграцию с Anki
    print("\n🎴 Проверка интеграции с Anki:")
    try:
        if word_analyzer.init_anki_integration():
            print("✅ Anki интеграция настроена")
        else:
            print("⚠️ Anki интеграция недоступна")
    except Exception as e:
        print(f"❌ Ошибка Anki интеграции: {e}")
    
    print("\n" + "=" * 50)
    print("🚀 Для полного функционала используйте:")
    print("   python -m spanish_analyser.cli")
    print("=" * 50)


def main():
    """Основная функция"""
    try:
        demo_analysis()
    except KeyboardInterrupt:
        print("\n\n👋 Работа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("Проверьте конфигурацию и зависимости")


if __name__ == "__main__":
    main()