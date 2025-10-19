"""
Демонстрация улучшенного логирования обработки Anki заметок.

Показывает детальный отчёт о том, какие заметки были исключены и почему.
"""

from spanish_analyser.components.anki_connector import AnkiConnector


def main():
    print("🔍 Демонстрация детального логирования Anki заметок")
    print("=" * 60)
    
    # Создаём коннектор
    connector = AnkiConnector()
    
    # Проверяем подключение
    if not connector.is_available():
        print("❌ Anki не запущен или AnkiConnect не установлен")
        print("💡 Запустите Anki и убедитесь, что плагин AnkiConnect активен")
        return
    
    print("✅ Подключение к Anki установлено")
    print("\n🔎 Извлекаем слова из испанских колод...")
    print("Теперь вы увидите детальный отчёт о том, какие заметки исключены и почему:")
    print("-" * 60)
    
    # Извлекаем слова с детальным логированием
    words = connector.extract_all_spanish_words("Spanish*")
    
    print("-" * 60)
    print(f"🎉 Результат: извлечено {len(words)} уникальных слов")
    
    if len(words) > 0:
        print(f"\n📝 Примеры первых 10 слов:")
        for i, word in enumerate(sorted(words)[:10], 1):
            print(f"  {i}. {word}")
    
    print("\n✅ Демонстрация завершена!")
    print("💡 Теперь вы точно знаете, почему некоторые заметки были исключены из обработки")


if __name__ == "__main__":
    main()
