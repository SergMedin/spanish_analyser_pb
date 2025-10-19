#!/usr/bin/env python3
"""
Демо-скрипт для веб-скрапера с проверкой Anki.

Перемещать в examples/ при следующем рефакторинге структуры.
"""

from spanish_analyser.anki_checker import check_anki_before_run
from spanish_analyser.config import config
from .practicatest_auth import PracticaTestAuth

def main():
    """Основная функция для тестирования веб-скрапера"""
    print("🌐 Тестирование веб-скрапера practicatest.com\n")
    
    # Проверяем, не запущено ли Anki
    print("🔍 Проверка состояния Anki...")
    if not check_anki_before_run():
        print("❌ Выполнение скрипта прервано.")
        return 1
    
    print("✅ Anki не запущено, можно продолжать...")
    
    # Тестируем веб-скрапер
    try:
        auth = PracticaTestAuth()
        
        print(f"\n🔗 Подключение к {auth.base_url}...")
        
        # Пытаемся войти в систему
        if auth.login():
            print("✅ Авторизация успешна!")
            
            # Получаем информацию о сессии
            session_info = auth.get_session_info()
            print(f"📊 Информация о сессии:")
            print(f"   Авторизован: {session_info['is_authenticated']}")
            print(f"   URL тестов: {session_info['tests_url']}")
            print(f"   Таймаут сессии: {session_info['session_timeout']} сек")
            
            if 'login_time' in session_info:
                print(f"   Время входа: {session_info['login_time']}")
                print(f"   Возраст сессии: {session_info['session_age']:.0f} сек")
                print(f"   Сессия действительна: {session_info['session_valid']}")
            
        else:
            print("❌ Авторизация не удалась")
            return 1
        
        # Закрываем сессию
        auth.close()
        print("✅ Сессия закрыта")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
