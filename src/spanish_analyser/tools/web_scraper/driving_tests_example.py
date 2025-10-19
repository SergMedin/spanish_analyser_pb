#!/usr/bin/env python3
"""
Пример использования веб-скрапера для загрузки тестов по вождению

Этот скрипт заменяет ваш старый downloader.ipynb и показывает,
как правильно загружать тесты по вождению с сайта practicatest.com
"""

import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from web_scraper import HTMLDownloader, ScrapingManager


def download_driving_tests_basic():
    """
    Базовый способ загрузки тестов по вождению
    (аналог вашего старого скрипта)
    """
    print("=== Загрузка тестов по вождению (базовый способ) ===\n")
    
    # Создаём загрузчик для сайта тестов по вождению
    downloader = HTMLDownloader(
        base_url="https://practicatest.com/tests/permiso-B/online",
        save_path="./data/driving_tests",
        delay_range=(3, 7),  # Увеличенные задержки для уважения сервера
        max_retries=3
    )
    
    try:
        # Загружаем 50 страниц (как в вашем старом скрипте)
        print("Начинаю загрузку 50 страниц с тестами...")
        print("Использую задержки 3-7 секунд между запросами для уважения сервера\n")
        
        downloaded_files = downloader.download_multiple_pages(
            num_pages=50,
            filename_pattern="driving_test_{}.html",
            delay=True
        )
        
        print(f"\n✅ Загрузка завершена!")
        print(f"📁 Загружено файлов: {len(downloaded_files)}")
        
        # Показываем статистику
        stats = downloader.get_stats()
        print(f"\n📊 Статистика загрузки:")
        print(f"   Успешных: {stats['successful']}")
        print(f"   Неудачных: {stats['failed']}")
        print(f"   Процент успеха: {stats['success_rate_percent']}%")
        print(f"   Путь сохранения: {stats['save_path']}")
        
        return downloaded_files
        
    finally:
        downloader.close()


def download_driving_tests_advanced():
    """
    Продвинутый способ с использованием менеджера скрапинга
    """
    print("\n=== Загрузка тестов по вождению (продвинутый способ) ===\n")
    
    # Создаём менеджер скрапинга
    manager = ScrapingManager(
        base_url="https://practicatest.com/tests/permiso-B/online",
        save_path="./data/driving_tests_advanced"
    )
    
    # Запускаем сессию скрапинга
    print("Запускаю продвинутую сессию скрапинга...")
    session_result = manager.start_scraping_session(
        session_name="driving_tests_advanced",
        num_pages=25,  # Меньше страниц для демонстрации
        delay_range=(4, 8),  # Ещё более уважительные задержки
        filename_pattern="advanced_test_{}.html"
    )
    
    print(f"✅ Сессия завершена: {session_result['status']}")
    
    # Показываем детальную информацию
    if 'stats' in session_result:
        stats = session_result['stats']
        print(f"\n📊 Детальная статистика:")
        print(f"   Успешных загрузок: {stats['successful']}")
        print(f"   Неудачных загрузок: {stats['failed']}")
        print(f"   Всего запросов: {stats['total_requests']}")
        print(f"   Процент успеха: {stats['success_rate_percent']}%")
    
    # Экспортируем метаданные
    manager.export_metadata_to_csv("driving_tests_summary.csv")
    print(f"\n📁 Метаданные экспортированы в CSV")
    
    return session_result


def download_with_parameters():
    """
    Пример загрузки с различными параметрами
    """
    print("\n=== Загрузка с параметрами ===\n")
    
    manager = ScrapingManager(
        base_url="https://practicatest.com/tests/permiso-B/online",
        save_path="./data/driving_tests_parameters"
    )
    
    # Список различных параметров для тестов
    test_parameters = [
        {"category": "traffic_signs", "level": "basic"},
        {"category": "traffic_rules", "level": "intermediate"},
        {"category": "safety", "level": "advanced"},
        {"category": "emergency", "level": "expert"}
    ]
    
    print("Загружаю страницы с различными параметрами...")
    session_result = manager.scrape_with_parameters(
        session_name="parameter_based_tests",
        parameters_list=test_parameters,
        delay_range=(3, 6)
    )
    
    print(f"✅ Скрапинг с параметрами завершён: {session_result['status']}")
    
    # Показываем результаты
    if 'results' in session_result:
        print(f"\n📄 Результаты загрузки:")
        for result in session_result['results']:
            status_emoji = "✅" if result['status'] == 'success' else "❌"
            params_str = ", ".join([f"{k}={v}" for k, v in result['params'].items()])
            print(f"   {status_emoji} {result['filename']}: {params_str}")
    
    return session_result


def show_final_summary():
    """Показывает итоговую сводку по всем сессиям"""
    print("\n=== Итоговая сводка ===\n")
    
    # Создаём менеджер для получения общей статистики
    manager = ScrapingManager(
        base_url="https://practicatest.com/tests/permiso-B/online",
        save_path="./data"
    )
    
    # Получаем общую статистику
    total_stats = manager.get_total_stats()
    
    print("📊 Общая статистика по всем сессиям:")
    print(f"   Всего сессий: {total_stats['total_sessions']}")
    print(f"   Завершённых: {total_stats['completed_sessions']}")
    print(f"   Неудачных: {total_stats['failed_sessions']}")
    print(f"   Всего загружено файлов: {total_stats['total_downloaded_files']}")
    print(f"   Средний процент успеха: {total_stats['average_success_rate']}%")
    print(f"   Последнее обновление: {total_stats['last_updated']}")
    
    # Показываем сводку по сессиям
    sessions_summary = manager.get_all_sessions_summary()
    if sessions_summary:
        print(f"\n📋 Сводка по сессиям:")
        for session in sessions_summary:
            status_emoji = "✅" if session['status'] == 'completed' else "❌"
            print(f"   {status_emoji} {session['name']}: {session['status']}")


def main():
    """Основная функция"""
    print("🚗 Инструмент для загрузки тестов по вождению\n")
    print("Этот скрипт заменяет ваш старый downloader.ipynb\n")
    
    try:
        # Способ 1: Базовый (как в старом скрипте)
        basic_files = download_driving_tests_basic()
        
        # Способ 2: Продвинутый с менеджером
        advanced_result = download_driving_tests_advanced()
        
        # Способ 3: С параметрами
        params_result = download_with_parameters()
        
        # Показываем итоговую сводку
        show_final_summary()
        
        print("\n🎉 Все загрузки завершены успешно!")
        print("\n📁 Результаты сохранены в папках:")
        print("   - ./data/driving_tests/ (базовый способ)")
        print("   - ./data/driving_tests_advanced/ (продвинутый способ)")
        print("   - ./data/driving_tests_parameters/ (с параметрами)")
        print("   - ./data/driving_tests_summary.csv (сводка)")
        print("   - ./data/scraping_metadata.json (метаданные)")
        
        print("\n💡 Теперь вместо старого downloader.ipynb используйте:")
        print("   from tools.web_scraper import HTMLDownloader")
        print("   downloader = HTMLDownloader(base_url='...', save_path='...')")
        print("   downloader.download_multiple_pages(num_pages=50)")
        
    except Exception as e:
        print(f"\n❌ Произошла ошибка: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
