#!/usr/bin/env python3
"""
Утилита для тестирования соединения с OpenAI API.

Проверяет:
- Наличие API ключа
- Доступность API
- Статус квоты
- Доступность разных моделей
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parents[2]))
sys.path.insert(0, str(Path(__file__).parents[2] / "tools" / "anki_deck_generator"))

from openai_helper import generate_front_and_back, QuotaExceededError
from spanish_analyser.config import config
from dotenv import load_dotenv


def test_openai_connection():
    """Тестирует соединение с OpenAI API."""
    
    print("🧪 Тестирование OpenAI API\n")
    
    # Загружаем переменные окружения
    load_dotenv()
    
    # Проверяем наличие API ключа
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or not api_key.strip():
        print("❌ OPENAI_API_KEY не найден в переменных окружения")
        print("💡 Создайте файл .env с содержимым:")
        print("   OPENAI_API_KEY=your_api_key_here")
        return False
    
    # Маскируем ключ для показа
    masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
    print(f"🔑 API ключ найден: {masked_key}")
    
    # Получаем настройки из конфигурации
    default_model = config.get_ai_model()
    print(f"🧠 Модель по умолчанию: {default_model}")
    
    # Тестируем базовое соединение
    try:
        print("\n📡 Отправляем тестовый запрос...")
        result = generate_front_and_back("test", front_text="test", model="gpt-3.5-turbo", pos="noun")
        print("✅ Базовый тест прошёл успешно")
        print(f"   Ответ: {result[1][:100]}..." if len(result[1]) > 100 else f"   Ответ: {result[1]}")
        
    except QuotaExceededError as e:
        print(f"💰 {e}")
        print("\n🔧 Для решения проблемы:")
        print("   1. Откройте https://platform.openai.com/account/billing")
        print("   2. Пополните баланс или обновите план")
        print("   3. Повторите тест после пополнения")
        return False
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False
    
    # Тестируем разные модели
    print("\n🧠 Тестируем доступность моделей...")
    models_to_test = ["gpt-3.5-turbo", "gpt-4", default_model]
    models_to_test = list(set(models_to_test))  # убираем дубликаты
    
    for model in models_to_test:
        try:
            result = generate_front_and_back("hola", front_text="hola", model=model, pos="interjection")
            print(f"   ✅ {model}: доступна")
        except QuotaExceededError:
            print(f"   💰 {model}: квота исчерпана")
        except Exception as e:
            if "does not exist" in str(e).lower() or "invalid" in str(e).lower():
                print(f"   ❌ {model}: модель недоступна")
            else:
                print(f"   ⚠️  {model}: {str(e)[:50]}...")
    
    print("\n🎉 Тестирование завершено успешно!")
    return True


def show_cache_status():
    """Показывает статус кэша OpenAI."""
    try:
        from spanish_analyser.cache import CacheManager
        cache = CacheManager.get_cache()
        stats = cache.stats_dict()
        
        print("\n📊 Статус кэша OpenAI:")
        openai_stats = stats['by_bucket'].get('openai', {})
        if openai_stats.get('hits', 0) > 0 or openai_stats.get('stores', 0) > 0:
            print(f"   Hits: {openai_stats.get('hits', 0)}")
            print(f"   Stores: {openai_stats.get('stores', 0)}")
            openai_size = stats['sizes'].get('openai', {})
            print(f"   Файлов: {openai_size.get('files', 0)}")
            print(f"   Размер: {openai_size.get('size_mb', 0)} MB")
        else:
            print("   Кэш пуст")
            
    except Exception as e:
        print(f"⚠️  Не удалось получить статус кэша: {e}")


if __name__ == "__main__":
    if test_openai_connection():
        show_cache_status()
        print("\n✅ Всё готово для работы с OpenAI API")
    else:
        print("\n❌ Проблемы с OpenAI API. Исправьте их перед использованием.")
        sys.exit(1)
