#!/usr/bin/env python3
__test__ = False  # отключаем сбор pytest: это модуль ядра, не тест
"""
Модуль для загрузки тестов по датам на practicatest.com

Предоставляет функционал для:
- Анализа таблицы тестов
- Проверки существующих загрузок
- Загрузки новых тестов
- Сохранения в папку data/downloads
"""

import os
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)


class TestDownloader:
    """Класс для загрузки тестов по датам"""
    
    def __init__(self, auth_session: Optional[requests.Session] = None, downloads_path: str = None) -> None:
        """
        Инициализация загрузчика тестов
        
        Args:
            auth_session: Сессия requests с авторизацией
            downloads_path: Путь к папке для загрузок
        """
        from spanish_analyser.config import config
        self.session = auth_session
        self.base_url = "https://practicatest.com"
        # Если путь не указан — берём из конфигурации
        resolved_path = downloads_path or config.get_downloads_folder()
        self.downloads_path = Path(resolved_path)
        
        # Создаём папку для загрузок если её нет
        self.downloads_path.mkdir(parents=True, exist_ok=True)
        
        # Формат названия файлов: test_YYYY-MM-DD.html
        self.filename_pattern = r"test_(\d{4})-(\d{2})-(\d{2})\.html"
        
        logger.info(f"🚀 Загрузчик тестов инициализирован для папки: {self.downloads_path}")
    
    def parse_tests_table(self, table_html: str) -> List[Dict[str, Any]]:
        """
        Парсит таблицу тестов и извлекает информацию о доступных тестах
        
        Args:
            table_html: HTML таблицы с тестами
            
        Returns:
            Список словарей с информацией о тестах
        """
        try:
            logger.info("🔍 Начинаю парсинг таблицы тестов...")
            
            soup = BeautifulSoup(table_html, 'html.parser')
            tests_data = []
            
            # Ищем все строки таблицы
            rows = soup.find_all('tr')
            logger.info(f"📊 Найдено строк в таблице: {len(rows)}")
            
            for i, row in enumerate(rows):
                # Пропускаем заголовки
                if i == 0:
                    continue
                    
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 5:  # Таблица имеет 5 колонок
                    # Извлекаем дату из первой ячейки
                    date_cell = cells[0].get_text(strip=True)
                    
                    # Проверяем, что это дата (формат DD-MM-YYYY)
                    if re.match(r'\d{2}-\d{2}-\d{4}', date_cell):
                        # Извлекаем статус из второй ячейки
                        status = cells[1].get_text(strip=True)
                        
                        # Ищем кнопку в пятой ячейке (последняя колонка)
                        action_cell = cells[4]
                        
                        # Детальное логирование для отладки
                        logger.info(f"Анализирую ячейку действия для даты {date_cell}: '{action_cell.get_text(strip=True)}'")
                        
                        # Ищем все кнопки и ссылки во ВСЕЙ строке (не только в последней ячейке)
                        buttons = row.find_all(['button', 'a'])
                        
                        if buttons:
                            for button in buttons:
                                button_text = button.get_text(strip=True).strip()
                                
                                # Определяем тип кнопки
                                # Кнопка TEST имеет текст "TEST >" или "TEST"
                                if 'test' in button_text.lower() and not 'login' in button_text.lower():
                                    button_type = "TEST"
                                elif 'login' in button_text.lower():
                                    button_type = "Premium"
                                else:
                                    button_type = "Unknown"
                                
                                # Получаем ссылку если есть
                                href = button.get('href', '')
                                onclick = button.get('onclick', '')
                                
                                test_info = {
                                    'date': date_cell,
                                    'status': status,
                                    'button_type': button_type,
                                    'button_text': button_text,
                                    'href': href,
                                    'onclick': onclick,
                                    'raw_html': str(row),
                                    'row_index': i
                                }
                                tests_data.append(test_info)
                                
                                logger.info(f"✅ Найден тест: {date_cell} - {button_type} - '{button_text}'")
                        else:
                            logger.info(f"В строке для даты {date_cell} не найдено кнопок")
            
            logger.info(f"✅ Найдено {len(tests_data)} тестов в таблице")
            return tests_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка при парсинге таблицы: {e}")
            return []
    
    def get_existing_downloads(self) -> List[str]:
        """
        Получает список уже загруженных дат
        
        Returns:
            Список дат в формате YYYY-MM-DD
        """
        try:
            existing_dates = []
            
            # Ищем файлы с нужным форматом
            for file_path in self.downloads_path.glob("test_*.html"):
                filename = file_path.name
                match = re.match(self.filename_pattern, filename)
                
                if match:
                    year, month, day = match.groups()
                    date_str = f"{year}-{month}-{day}"
                    existing_dates.append(date_str)
            
            logger.info(f"✅ Найдено {len(existing_dates)} уже загруженных тестов")
            return existing_dates
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении списка загрузок: {e}")
            return []
    
    def convert_date_format(self, date_str: str) -> str:
        """
        Конвертирует дату из формата DD-MM-YYYY в YYYY-MM-DD
        
        Args:
            date_str: Дата в формате DD-MM-YYYY
            
        Returns:
            Дата в формате YYYY-MM-DD
        """
        try:
            # Парсим дату DD-MM-YYYY
            day, month, year = date_str.split('-')
            return f"{year}-{month}-{day}"
        except Exception as e:
            logger.error(f"❌ Ошибка конвертации даты {date_str}: {e}")
            return date_str
    
    def get_downloadable_tests(self, tests_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Определяет какие тесты можно загрузить
        
        Args:
            tests_data: Список всех тестов
            
        Returns:
            Список тестов для загрузки
        """
        try:
            existing_dates = self.get_existing_downloads()
            downloadable_tests = []
            
            for test in tests_data:
                # Конвертируем дату в нужный формат
                test_date = self.convert_date_format(test['date'])
                
                # Проверяем, можно ли загрузить тест
                if (test['button_type'] == "TEST" and 
                    test_date not in existing_dates):
                    downloadable_tests.append({
                        **test,
                        'download_date': test_date
                    })
            
            logger.info(f"✅ Найдено {len(downloadable_tests)} тестов для загрузки")
            return downloadable_tests
            
        except Exception as e:
            logger.error(f"❌ Ошибка при определении загружаемых тестов: {e}")
            return []
    
    def download_test_page(self, test_info: Dict[str, Any]) -> bool:
        """
        Загружает страницу теста
        
        Args:
            test_info: Информация о тесте
            
        Returns:
            True если загрузка успешна
        """
        try:
            date_str = test_info['download_date']
            original_date = test_info['date']
            
            logger.info(f"📥 Загружаю тест за {original_date}...")
            
            # Формируем URL для теста
            # Кнопка Test ведёт на /tests/permiso-B/online
            if test_info['button_type'] == "TEST":
                test_url = test_info['href']
                if not test_url:
                    test_url = f"{self.base_url}/tests/permiso-B/online"
                
                # Добавляем параметр даты если нужно
                if '?' not in test_url:
                    test_url += f"?date={date_str}"
                else:
                    test_url += f"&date={date_str}"
                    
            else:
                logger.warning(f"Пропускаю тест за {original_date} - тип кнопки: {test_info['button_type']}")
                return False
            
            logger.info(f"URL для загрузки: {test_url}")
            
            # Загружаем страницу
            response = self.session.get(test_url, timeout=30)
            response.raise_for_status()
            
            if response.status_code == 200:
                # Очищаем HTML от изображений
                clean_html = self.clean_html_content(response.text)
                
                # Формируем имя файла
                filename = f"test_{date_str}.html"
                file_path = self.downloads_path / filename
                
                # Сохраняем файл
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(clean_html)
                
                logger.info(f"✅ Тест за {original_date} сохранён в {filename}")
                return True
            else:
                logger.error(f"❌ Ошибка загрузки теста за {original_date}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке теста за {test_info.get('date', 'неизвестная дата')}: {e}")
            return False
    
    def clean_html_content(self, html_content: str) -> str:
        """
        Очищает HTML от изображений и лишнего контента
        
        Args:
            html_content: Исходный HTML
            
        Returns:
            Очищенный HTML
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Удаляем все изображения
            for img in soup.find_all('img'):
                img.decompose()
            
            # Удаляем скрипты
            for script in soup.find_all('script'):
                script.decompose()
            
            # Удаляем стили
            for style in soup.find_all('style'):
                style.decompose()
            
            # Удаляем iframe
            for iframe in soup.find_all('iframe'):
                iframe.decompose()
            
            # Удаляем canvas
            for canvas in soup.find_all('canvas'):
                canvas.decompose()
            
            # Удаляем svg
            for svg in soup.find_all('svg'):
                svg.decompose()
            
            # Удаляем комментарии
            for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
                comment.extract()
            
            logger.info("✅ HTML очищен от изображений и лишнего контента")
            return str(soup)
            
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке HTML: {e}")
            return html_content
    
    def download_all_available_tests(self, tests_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Загружает все доступные тесты
        
        Args:
            tests_data: Список всех тестов
            
        Returns:
            Словарь с результатами загрузки
        """
        try:
            logger.info("Начинаю загрузку всех доступных тестов...")
            
            # Получаем список тестов для загрузки
            downloadable_tests = self.get_downloadable_tests(tests_data)
            
            if not downloadable_tests:
                logger.info("ℹ️ Нет новых тестов для загрузки")
                return {
                    'total_tests': len(tests_data),
                    'existing_tests': len(self.get_existing_downloads()),
                    'new_tests': 0,
                    'downloaded_tests': 0,
                    'failed_tests': 0
                }
            
            # Загружаем каждый тест
            downloaded_count = 0
            failed_count = 0
            
            for test in downloadable_tests:
                if self.download_test_page(test):
                    downloaded_count += 1
                else:
                    failed_count += 1
            
            # Формируем отчёт
            report = {
                'total_tests': len(tests_data),
                'existing_tests': len(self.get_existing_downloads()),
                'new_tests': len(downloadable_tests),
                'downloaded_tests': downloaded_count,
                'failed_tests': failed_count,
                'downloadable_tests': downloadable_tests
            }
            
            logger.info(f"✅ Загрузка завершена: {downloaded_count} успешно, {failed_count} неудачно")
            return report
            
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке тестов: {e}")
            return {}
    
    def print_download_report(self, tests_data: List[Dict[str, Any]]):
        """
        Выводит отчёт о загрузке в консоль
        
        Args:
            tests_data: Список всех тестов
        """
        try:
            existing_dates = self.get_existing_downloads()
            downloadable_tests = self.get_downloadable_tests(tests_data)
            
            print("\n" + "="*60)
            print("📊 ОТЧЁТ О ЗАГРУЗКЕ ТЕСТОВ")
            print("="*60)
            
            # Анализируем все тесты
            test_tests = [t for t in tests_data if t['button_type'] == "TEST"]
            premium_tests = [t for t in tests_data if t['button_type'] == "Premium"]
            
            print(f"📋 Всего тестов в таблице: {len(tests_data)}")
            print(f"🔘 Тестов с кнопкой TEST: {len(test_tests)}")
            print(f"⭐ Тестов с кнопкой Premium: {len(premium_tests)}")
            print(f"📁 Уже загружено: {len(existing_dates)}")
            print(f"🚀 Доступно для загрузки: {len(downloadable_tests)}")
            
            if existing_dates:
                print(f"\n📅 Уже загруженные даты:")
                for date in sorted(existing_dates)[:10]:  # Показываем первые 10
                    print(f"  ✅ {date}")
                if len(existing_dates) > 10:
                    print(f"  ... и ещё {len(existing_dates) - 10}")
            
            if downloadable_tests:
                print(f"\n🎯 Тесты для загрузки:")
                for test in downloadable_tests[:10]:  # Показываем первые 10
                    print(f"  🔘 {test['date']} -> {test['download_date']}")
                if len(downloadable_tests) > 10:
                    print(f"  ... и ещё {len(downloadable_tests) - 10}")
                
                print(f"\n💡 Начинаю загрузку {len(downloadable_tests)} тестов...")
            else:
                print(f"\nℹ️ Все доступные тесты уже загружены!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при формировании отчёта: {e}")
    
    def get_test_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по загруженным тестам
        
        Returns:
            Словарь со статистикой
        """
        try:
            existing_dates = self.get_existing_downloads()
            
            # Анализируем файлы по датам
            stats = {
                'total_files': len(existing_dates),
                'oldest_date': min(existing_dates) if existing_dates else None,
                'newest_date': max(existing_dates) if existing_dates else None,
                'date_range': None
            }
            
            if stats['oldest_date'] and stats['newest_date']:
                oldest = datetime.strptime(stats['oldest_date'], '%Y-%m-%d')
                newest = datetime.strptime(stats['newest_date'], '%Y-%m-%d')
                stats['date_range'] = (newest - oldest).days + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении статистики: {e}")
            return {}
