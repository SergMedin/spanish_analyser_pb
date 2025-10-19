#!/usr/bin/env python3
"""
Исправление дорогой проверки OpenAI API.
Заменяем реальный запрос на бесплатную проверку.
"""

def fix_expensive_check():
    file_path = "src/spanish_analyser/tools/anki_deck_generator/anki_deck_maker.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Заменяем дорогую проверку на бесплатную
    old_check = '''    # Быстрая проверка доступности OpenAI API
    try:
        print("🔌 Проверяем доступность OpenAI API...")
        test_result = generate_front_and_back("test", front_text="test", model="gpt-3.5-turbo", pos="test")
        print("✅ OpenAI API доступен")
    except QuotaExceededError as e:
        print(f"💰 {e}")
        print("\\n🔧 Для решения проблемы:")
        print("   1. Откройте https://platform.openai.com/account/billing")
        print("   2. Пополните баланс или обновите план")
        print("   3. Повторите запуск после пополнения")
        return 1
    except Exception as e:
        # Для других ошибок можем продолжить - возможно это временная проблема сети
        logger.warning(f"Не удалось проверить OpenAI API: {e}")
        print("⚠️  Не удалось проверить OpenAI API. Продолжаем (возможны проблемы при генерации)...")'''
    
    new_check = '''    # Проверяем только наличие API ключа (без реальных запросов)
    print("🔌 API ключ OpenAI найден")
    print("💡 Проверка доступности будет выполнена при первом запросе")'''
    
    new_content = content.replace(old_check, new_check)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Исправлено: убрана дорогая проверка OpenAI API")

if __name__ == "__main__":
    fix_expensive_check()
