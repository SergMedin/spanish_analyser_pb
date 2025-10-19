#!/usr/bin/env python3
"""
Простой тест для проверки статуса OpenAI API.
Проверяет доступность API, лимиты и текущий статус аккаунта.
"""

import os
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from openai import OpenAI
import json

def test_openai_api():
    """Тестирует доступность и статус OpenAI API."""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or not api_key.strip():
        print("❌ OPENAI_API_KEY не найден в переменных окружения")
        print("📋 Создайте файл .env с содержимым:")
        print("   OPENAI_API_KEY=your_api_key_here")
        return False
    
    # Маскируем ключ для показа
    masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
    print(f"🔑 API ключ найден: {masked_key}")
    
    try:
        client = OpenAI(api_key=api_key)
        print("🔌 Клиент OpenAI создан")
        
        # Простой тестовый запрос
        print("📡 Отправляем тестовый запрос...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Используем более дешёвую модель для теста
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello' in Spanish."}
            ],
            max_tokens=10
        )
        
        print("✅ API работает!")
        print(f"📨 Ответ модели: {response.choices[0].message.content}")
        print(f"🏷️  Модель: {response.model}")
        print(f"🎫 Токены: {response.usage.total_tokens}")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Ошибка при обращении к OpenAI API:")
        print(f"   {error_msg}")
        
        # Анализируем тип ошибки
        if "insufficient_quota" in error_msg.lower():
            print("\n💰 ДИАГНОЗ: Превышена квота OpenAI")
            print("📋 Возможные причины:")
            print("   1. Исчерпан бесплатный лимит ($5)")
            print("   2. Исчерпан месячный лимит платного плана")
            print("   3. Проблемы с оплатой или картой")
            print("\n🔧 Что делать:")
            print("   1. Проверьте баланс: https://platform.openai.com/account/billing")
            print("   2. Проверьте лимиты: https://platform.openai.com/account/rate-limits")
            print("   3. Пополните баланс или обновите план")
            
        elif "429" in error_msg:
            print("\n⏱️  ДИАГНОЗ: Rate limiting")
            print("📋 Слишком много запросов за короткое время")
            print("🔧 Попробуйте через несколько минут")
            
        elif "401" in error_msg or "invalid" in error_msg.lower():
            print("\n🔐 ДИАГНОЗ: Неверный API ключ")
            print("🔧 Проверьте корректность ключа в .env файле")
            
        else:
            print(f"\n🤷 Неизвестная ошибка, обратитесь к документации OpenAI")
            
        return False

def check_model_availability():
    """Проверяет доступность различных моделей."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return
        
    try:
        client = OpenAI(api_key=api_key)
        print("\n🧠 Проверяем доступность моделей...")
        
        models_to_test = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
        
        for model in models_to_test:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=1
                )
                print(f"   ✅ {model}: доступна")
            except Exception as e:
                if "insufficient_quota" in str(e).lower():
                    print(f"   💰 {model}: квота исчерпана")
                elif "does not exist" in str(e).lower():
                    print(f"   ❌ {model}: модель не найдена")
                else:
                    print(f"   ⚠️  {model}: {str(e)[:50]}...")
                    
    except Exception as e:
        print(f"❌ Не удалось проверить модели: {e}")

if __name__ == "__main__":
    print("🧪 Тестирование OpenAI API\n")
    
    if test_openai_api():
        check_model_availability()
        print("\n🎉 Тест завершён успешно")
    else:
        print("\n💥 Тест не пройден")
        sys.exit(1)
