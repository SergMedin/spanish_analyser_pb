#!/usr/bin/env python3
"""
Специализированный загрузчик для билетов по вождению

Расширение универсального web_scraper для работы с билетами
по вождению с сайта practicatest.com
"""

from .html_downloader import HTMLDownloader
from .scraping_manager import ScrapingManager
from .practicatest_auth import PracticaTestAuth
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DrivingTestsDownloader(HTMLDownloader):
    """Специализированный загрузчик для билетов по вождению"""
    
    def __init__(self, 
                 save_path: str = None,
                 delay_range: tuple = (3, 7),
                 max_retries: int = 3,
                 config_file: str = None):
        """
        Инициализация загрузчика для билетов по вождению
        
        Args:
            save_path: Путь для сохранения файлов
            delay_range: Диапазон задержек между запросами (в секундах)
            max_retries: Максимальное количество повторных попыток
            config_file: Путь к файлу конфигурации для авторизации (по умолчанию ищет .env в корневой папке)
        """
        # Базовый URL для билетов по вождению
        base_url = "https://practicatest.com/tests/permiso-B/online"
        
        # Если путь не указан — берём из конфигурации
        if save_path is None:
            from spanish_analyser.config import config
            save_path = config.get_downloads_folder()
        # Вызываем конструктор родительского класса
        super().__init__(
            base_url=base_url,
            save_path=save_path,
            delay_range=delay_range,
            max_retries=max_retries
        )
        
        # Инициализируем модуль авторизации
        self.auth = PracticaTestAuth(config_file)
        
        logger.info(f"Загрузчик билетов по вождению инициализирован")
        logger.info(f"Базовый URL: {base_url}")
        logger.info(f"Файлы будут сохраняться в: {save_path}")
    
    def download_test_page(self, page_number: int, filename: str = None) -> bool:
        """
        Загружает одну страницу с билетом
        
        Args:
            page_number: Номер страницы
            filename: Имя файла для сохранения
            
        Returns:
            True если загрузка успешна, False в противном случае
        """
        if not filename:
            filename = f"driving_test_{page_number:03d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # Проверяем авторизацию перед загрузкой
        if not self._ensure_authenticated():
            logger.error("Не удалось авторизоваться для загрузки страницы")
            return False
        
        # Формируем URL для страницы
        url = f"{self.base_url}?page={page_number}"
        
        # Используем метод родительского класса
        return self.download_page(url=url, filename=filename)
    
    def download_multiple_tests(self, start_page: int, end_page: int, 
                               delay: bool = True) -> list:
        """
        Загружает несколько страниц с билетами
        
        Args:
            start_page: Начальная страница
            end_page: Конечная страница
            delay: Использовать ли задержки между запросами
            
        Returns:
            Список успешно загруженных файлов
        """
        logger.info(f"Начинаю загрузку билетов с {start_page} по {end_page}")
        
        downloaded_files = []
        
        for page_num in range(start_page, end_page + 1):
            # Генерируем имя файла с датой
            filename = f"driving_test_{page_num:03d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            if self.download_test_page(page_num, filename):
                downloaded_files.append(filename)
            
            # Задержка между запросами (если включена)
            if delay and page_num < end_page:
                import time
                import random
                delay_time = random.uniform(*self.delay_range)
                logger.info(f"Ожидание {delay_time:.1f} секунд...")
                time.sleep(delay_time)
        
        logger.info(f"Загрузка завершена. Успешно: {len(downloaded_files)}")
        return downloaded_files


class DrivingTestsScrapingManager(ScrapingManager):
    """Специализированный менеджер скрапинга для билетов по вождению"""
    
    def __init__(self, 
                 save_path: str = None,
                 metadata_file: str = "driving_tests_metadata.json"):
        """
        Инициализация менеджера скрапинга для билетов
        
        Args:
            save_path: Путь для сохранения результатов
            metadata_file: Имя файла с метаданными
        """
        base_url = "https://practicatest.com/tests/permiso-B/online"
        
        # Если путь не указан — берём из конфигурации
        if save_path is None:
            from spanish_analyser.config import config
            save_path = config.get_downloads_folder()
        # Вызываем конструктор родительского класса
        super().__init__(
            base_url=base_url,
            save_path=save_path,
            metadata_file=metadata_file
        )
        
        logger.info(f"Менеджер скрапинга билетов по вождению инициализирован")
    
    def scrape_driving_tests(self, start_page: int, end_page: int, 
                            delay_range: tuple = (3, 7)) -> dict:
        """
        Специализированный метод для скрапинга билетов по вождению
        
        Args:
            start_page: Начальная страница
            end_page: Конечная страница
            delay_range: Диапазон задержек между запросами
            
        Returns:
            Результат скрапинга
        """
        session_name = f"driving_tests_{start_page}_{end_page}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Создаём загрузчик
        downloader = DrivingTestsDownloader(
            save_path=str(self.save_path),
            delay_range=delay_range
        )
        
        try:
            # Загружаем билеты
            downloaded_files = downloader.download_multiple_tests(start_page, end_page, delay=True)
            
            # Получаем статистику
            stats = downloader.get_stats()
            
            # Сохраняем сессию
            session_data = {
                'name': session_name,
                'start_page': start_page,
                'end_page': end_page,
                'downloaded_files': downloaded_files,
                'stats': stats,
                'status': 'completed' if downloaded_files else 'failed',
                'timestamp': datetime.now().isoformat()
            }
            
            self.metadata['sessions'].append(session_data)
            self._save_metadata()
            
            return session_data
            
        finally:
            downloader.close()
    
    def _ensure_authenticated(self) -> bool:
        """
        Обеспечивает авторизацию перед загрузкой
        
        Returns:
            True если авторизация активна
        """
        # Проверяем текущую сессию
        if self.auth.is_session_valid():
            logger.debug("Сессия активна, авторизация не требуется")
            return True
        
        # Пытаемся войти в систему
        logger.info("Требуется авторизация, выполняю вход...")
        if self.auth.login():
            logger.info("✅ Авторизация успешна")
            return True
        else:
            logger.error("❌ Не удалось авторизоваться")
            return False
    
    def get_auth_status(self) -> dict:
        """
        Возвращает статус авторизации
        
        Returns:
            Словарь с информацией об авторизации
        """
        return self.auth.get_session_info()
    
    def close(self):
        """Закрывает загрузчик и сессию авторизации"""
        try:
            # Закрываем родительский класс
            super().close()
            # Закрываем авторизацию
            self.auth.close()
            logger.info("Загрузчик билетов по вождению закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии загрузчика: {e}")
