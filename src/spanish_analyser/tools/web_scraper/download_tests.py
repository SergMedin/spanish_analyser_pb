#!/usr/bin/env python3
"""
Основной скрипт для загрузки тестов practicatest.com

Этот скрипт:
1. Авторизуется на practicatest.com
2. Получает таблицу доступных тестов
3. Проверяет уже загруженные тесты
4. Загружает новые тесты с кнопкой TEST
5. Пропускает тесты с кнопкой Premium
6. Сохраняет тесты в папку data/downloads
"""

import logging
from pathlib import Path

# Логирование конфигурируется централизованно через spanish_analyser.config

from .practicatest_auth import PracticaTestAuth
from .practicatest_parser import PracticaTestParser
from .test_downloader import TestDownloader
from spanish_analyser.config import config


def download_available_tests():
    """
    Основная функция для загрузки доступных тестов
    
    Returns:
        True если загрузка прошла успешно
    """
    print("🚀 Загрузка доступных тестов practicatest.com")
    print("=" * 60)
    
    # Проверяем наличие .env файла
    project_root = Path(__file__).parent.parent.parent.parent.parent
    env_file = project_root / ".env"
    
    if not env_file.exists():
        print("⚠️  Файл .env не найден!")
        print("💡 Создайте файл .env с вашими данными для входа:")
        print("   PRACTICATEST_EMAIL=ваш_email@example.com")
        print("   PRACTICATEST_PASSWORD=ваш_пароль")
        return False
    
    print(f"✅ Файл .env найден: {env_file.absolute()}")
    
    # Создаём экземпляр авторизации
    auth = PracticaTestAuth()
    
    try:
        # Авторизуемся
        print("\n🔐 Шаг 1: Авторизация...")
        if not auth.login():
            print("❌ Авторизация не удалась")
            return False
        
        print("✅ Авторизация успешна!")
        
        # Создаём парсер
        print("\n🔍 Шаг 2: Создание парсера...")
        parser = PracticaTestParser(auth.session)
        print("✅ Парсер создан")
        
        # Получаем таблицу с тестами
        print("\n📋 Шаг 3: Получение таблицы тестов...")
        table = parser.get_tests_table()
        
        if not table:
            print("❌ Таблица с тестами не найдена")
            return False
        
        print("✅ Таблица с тестами получена")
        
        # Создаём загрузчик тестов
        print("\n📥 Шаг 4: Создание загрузчика тестов...")
        # Берём путь к загрузкам из config.yaml
        downloads_path = Path(config.get_downloads_folder())
        downloader = TestDownloader(auth.session, str(downloads_path))
        print("✅ Загрузчик тестов создан")
        
        # Парсим таблицу тестов
        print("\n🔍 Шаг 5: Парсинг таблицы тестов...")
        table_html = str(table)
        tests_data = downloader.parse_tests_table(table_html)
        
        if not tests_data:
            print("❌ Данные тестов не найдены")
            return False
        
        print(f"✅ Найдено {len(tests_data)} тестов в таблице")
        
        # Анализируем типы кнопок
        test_tests = [t for t in tests_data if t['button_type'] == "TEST"]
        premium_tests = [t for t in tests_data if t['button_type'] == "Premium"]
        
        print(f"\n📊 Анализ таблицы:")
        print(f"  🔘 Тестов с кнопкой TEST: {len(test_tests)}")
        print(f"  ⭐ Тестов с кнопкой Premium: {len(premium_tests)}")
        
        # Выводим отчёт о загрузке
        print("\n📊 Шаг 6: Отчёт о загрузке...")
        downloader.print_download_report(tests_data)
        
        # Если есть тесты для загрузки, начинаем загрузку
        if test_tests:
            print("\n🚀 Шаг 7: Начинаю загрузку тестов...")
            
            # Загружаем все доступные тесты
            report = downloader.download_all_available_tests(tests_data)
            
            if report:
                print(f"\n📈 Результаты загрузки:")
                print(f"  📋 Всего тестов в таблице: {report['total_tests']}")
                print(f"  📁 Уже загружено: {report['existing_tests']}")
                print(f"  🚀 Новых тестов: {report['new_tests']}")
                print(f"  ✅ Успешно загружено: {report['downloaded_tests']}")
                print(f"  ❌ Ошибок загрузки: {report['failed_tests']}")
            
            # Получаем статистику
            stats = downloader.get_test_statistics()
            if stats:
                print(f"\n📊 Статистика загруженных тестов:")
                print(f"  📁 Всего файлов: {stats['total_files']}")
                if stats['oldest_date']:
                    print(f"  📅 Самая старая дата: {stats['oldest_date']}")
                if stats['newest_date']:
                    print(f"  📅 Самая новая дата: {stats['newest_date']}")
                if stats['date_range'] is not None:
                    print(f"  📅 Диапазон дат: {stats['date_range']} дней")
        else:
            print("\nℹ️ Нет доступных тестов для загрузки!")
        
        print("\n🎉 Загрузка тестов завершена!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при загрузке тестов: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Закрываем сессию
        auth.close()
        print("\n🔒 Сессия закрыта")


def main():
    """Главная функция"""
    success = download_available_tests()
    
    if success:
        print("\n✅ Загрузка тестов прошла успешно!")
        sys.exit(0)
    else:
        print("\n❌ Загрузка тестов не удалась!")
        sys.exit(1)


if __name__ == "__main__":
    main()
