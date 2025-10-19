#!/usr/bin/env python3
"""
Основной скрипт для веб-скрапинга

Демонстрирует использование инструментов для загрузки HTML страниц
"""

import sys
from pathlib import Path

"""CLI для демонстрации возможностей web_scraper.

Этот файл остаётся точкой входа, а демо-скрипты перенесены в пакет examples/.
"""

# Добавляем путь к модулям пакета
sys.path.insert(0, str(Path(__file__).parent))

from web_scraper import HTMLDownloader, ScrapingManager


def demo_basic_download():
    """Демонстрация базовой загрузки страниц"""
    print("=== Демонстрация базовой загрузки ===\n")
    
    # Создаём загрузчик для тестового сайта
    downloader = HTMLDownloader(
        base_url="https://httpbin.org/html",
        save_path="./demo_downloads",
        delay_range=(1, 2)
    )
    
    try:
        # Загружаем одну страницу
        print("Загружаю тестовую страницу...")
        if downloader.download_page(filename="test_page.html"):
            print("✅ Страница успешно загружена!")
        
        # Показываем статистику
        stats = downloader.get_stats()
        print(f"\n📊 Статистика загрузки:")
        print(f"   Успешных: {stats['successful']}")
        print(f"   Неудачных: {stats['failed']}")
        print(f"   Всего запросов: {stats['total_requests']}")
        print(f"   Процент успеха: {stats['success_rate_percent']}%")
        
    finally:
        downloader.close()


def demo_scraping_manager():
    """Демонстрация менеджера скрапинга"""
    print("\n=== Демонстрация менеджера скрапинга ===\n")
    
    # Создаём менеджер
    manager = ScrapingManager(
        base_url="https://httpbin.org/html",
        save_path="./demo_scraping"
    )
    
    # Запускаем сессию скрапинга
    print("Запускаю сессию скрапинга...")
    session_result = manager.start_scraping_session(
        session_name="demo_session",
        num_pages=3,
        delay_range=(1, 2)
    )
    
    print(f"✅ Сессия завершена: {session_result['status']}")
    
    # Показываем сводку по всем сессиям
    print("\n📋 Сводка по сессиям:")
    sessions_summary = manager.get_all_sessions_summary()
    for session in sessions_summary:
        print(f"   {session['name']}: {session['status']}")
    
    # Экспортируем метаданные
    manager.export_metadata_to_csv("demo_summary.csv")
    print("\n📁 Метаданные экспортированы в CSV")
    
    # Показываем общую статистику
    total_stats = manager.get_total_stats()
    print(f"\n📊 Общая статистика:")
    print(f"   Всего сессий: {total_stats['total_sessions']}")
    print(f"   Завершённых: {total_stats['completed_sessions']}")
    print(f"   Неудачных: {total_stats['failed_sessions']}")
    print(f"   Всего файлов: {total_stats['total_downloaded_files']}")


def demo_parameter_based_scraping():
    """Демонстрация скрапинга с параметрами"""
    print("\n=== Демонстрация скрапинга с параметрами ===\n")
    
    manager = ScrapingManager(
        base_url="https://httpbin.org/get",
        save_path="./demo_parameters"
    )
    
    # Список параметров для тестирования
    parameters_list = [
        {"param1": "value1", "param2": "value2"},
        {"test": "data", "number": "123"},
        {"language": "spanish", "level": "beginner"}
    ]
    
    print("Запускаю скрапинг с параметрами...")
    session_result = manager.scrape_with_parameters(
        session_name="parameters_demo",
        parameters_list=parameters_list,
        delay_range=(1, 2)
    )
    
    print(f"✅ Скрапинг с параметрами завершён: {session_result['status']}")
    
    # Показываем результаты
    if 'results' in session_result:
        print(f"\n📄 Результаты:")
        for result in session_result['results']:
            status_emoji = "✅" if result['status'] == 'success' else "❌"
            print(f"   {status_emoji} {result['filename']}: {result['status']}")


def main():
    """Основная функция"""
    print("🌐 Инструмент для веб-скрапинга\n")
    
    try:
        # Демонстрируем различные возможности
        demo_basic_download()
        demo_scraping_manager()
        demo_parameter_based_scraping()
        
        print("\n🎉 Все демонстрации завершены успешно!")
        print("\n📁 Результаты сохранены в папках:")
        print("   - ./demo_downloads/")
        print("   - ./demo_scraping/")
        print("   - ./demo_parameters/")
        
    except Exception as e:
        print(f"\n❌ Произошла ошибка: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
