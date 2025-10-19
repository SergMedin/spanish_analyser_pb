"""
Модуль для загрузки HTML страниц

Предоставляет функциональность для:
- Загрузки HTML страниц с веб-сайтов
- Управления задержками между запросами
- Сохранения контента в файлы
- Обработки ошибок и повторных попыток
"""

import requests
import time
import random
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import logging

# Логгер модуля (конфигурируется централизованно через spanish_analyser.config)
logger = logging.getLogger(__name__)


class HTMLDownloader:
    """Класс для загрузки HTML страниц с веб-сайтов"""
    
    def __init__(self, 
                 base_url: str,
                 save_path: str = "./downloads",
                 delay_range: tuple = (1, 5),
                 max_retries: int = 3,
                 user_agent: Optional[str] = None):
        """
        Инициализация загрузчика
        
        Args:
            base_url: Базовый URL для загрузки
            save_path: Путь для сохранения файлов
            delay_range: Диапазон задержек между запросами (в секундах)
            max_retries: Максимальное количество повторных попыток
            user_agent: Пользовательский User-Agent
        """
        self.base_url = base_url
        self.save_path = Path(save_path)
        self.delay_range = delay_range
        self.max_retries = max_retries
        
        # Создаём папку для сохранения
        self.save_path.mkdir(parents=True, exist_ok=True)
        
        # Настройка сессии requests
        self.session = requests.Session()
        
        # Устанавливаем User-Agent
        if user_agent:
            self.session.headers.update({'User-Agent': user_agent})
        else:
            # Стандартный User-Agent для браузера
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
        
        # Статистика загрузок
        self.download_stats = {
            'successful': 0,
            'failed': 0,
            'total_requests': 0
        }
    
    def download_page(self, 
                     url: Optional[str] = None, 
                     filename: Optional[str] = None,
                     retry_count: int = 0) -> bool:
        """
        Загружает одну HTML страницу
        
        Args:
            url: URL для загрузки (если None, используется base_url)
            filename: Имя файла для сохранения
            retry_count: Текущий номер попытки
            
        Returns:
            True если загрузка успешна, False в противном случае
        """
        target_url = url or self.base_url
        
        try:
            logger.info(f"Загружаю страницу: {target_url}")
            
            # Выполняем запрос
            response = self.session.get(target_url, timeout=30)
            self.download_stats['total_requests'] += 1
            
            if response.status_code == 200:
                # Генерируем имя файла если не указано
                if not filename:
                    filename = self._generate_filename(target_url)
                
                # Сохраняем файл
                file_path = self.save_path / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                logger.info(f"Страница сохранена: {file_path}")
                self.download_stats['successful'] += 1
                return True
                
            else:
                logger.warning(f"Ошибка HTTP {response.status_code} для {target_url}")
                self.download_stats['failed'] += 1
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при загрузке {target_url}: {e}")
            
            # Повторная попытка если не превышен лимит
            if retry_count < self.max_retries:
                logger.info(f"Повторная попытка {retry_count + 1}/{self.max_retries}")
                time.sleep(random.uniform(2, 5))  # Увеличенная задержка при ошибке
                return self.download_page(url, filename, retry_count + 1)
            else:
                logger.error(f"Превышен лимит повторных попыток для {target_url}")
                self.download_stats['failed'] += 1
                return False
    
    def download_multiple_pages(self, 
                               num_pages: int,
                               filename_pattern: str = "page_{}.html",
                               delay: bool = True) -> List[str]:
        """
        Загружает несколько страниц
        
        Args:
            num_pages: Количество страниц для загрузки
            filename_pattern: Шаблон для имён файлов
            delay: Добавлять ли задержки между запросами
            
        Returns:
            Список путей к загруженным файлам
        """
        downloaded_files = []
        
        for i in range(1, num_pages + 1):
            filename = filename_pattern.format(i)
            
            if self.download_page(filename=filename):
                downloaded_files.append(str(self.save_path / filename))
            
            # Задержка между запросами
            if delay and i < num_pages:
                sleep_time = random.uniform(*self.delay_range)
                logger.info(f"Ожидание {sleep_time:.2f} секунд...")
                time.sleep(sleep_time)
        
        return downloaded_files
    
    def download_with_parameters(self, 
                                params: Dict[str, Any],
                                filename: str) -> bool:
        """
        Загружает страницу с параметрами запроса
        
        Args:
            params: Параметры для GET запроса
            filename: Имя файла для сохранения
            
        Returns:
            True если загрузка успешна, False в противном случае
        """
        try:
            logger.info(f"Загружаю страницу с параметрами: {params}")
            
            response = self.session.get(self.base_url, params=params, timeout=30)
            self.download_stats['total_requests'] += 1
            
            if response.status_code == 200:
                file_path = self.save_path / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                logger.info(f"Страница с параметрами сохранена: {file_path}")
                self.download_stats['successful'] += 1
                return True
            else:
                logger.warning(f"Ошибка HTTP {response.status_code}")
                self.download_stats['failed'] += 1
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке с параметрами: {e}")
            self.download_stats['failed'] += 1
            return False
    
    def _generate_filename(self, url: str) -> str:
        """
        Генерирует имя файла на основе URL
        
        Args:
            url: URL страницы
            
        Returns:
            Имя файла
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('.', '_')
        path = parsed_url.path.replace('/', '_').strip('_')
        
        if not path:
            path = 'index'
        
        timestamp = int(time.time())
        return f"{domain}_{path}_{timestamp}.html"
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получает статистику загрузок
        
        Returns:
            Словарь со статистикой
        """
        success_rate = 0
        if self.download_stats['total_requests'] > 0:
            success_rate = (self.download_stats['successful'] / 
                          self.download_stats['total_requests']) * 100
        
        return {
            **self.download_stats,
            'success_rate_percent': round(success_rate, 2),
            'save_path': str(self.save_path)
        }
    
    def clear_stats(self):
        """Сбрасывает статистику загрузок"""
        self.download_stats = {
            'successful': 0,
            'failed': 0,
            'total_requests': 0
        }
    
    def close(self):
        """Закрывает сессию requests"""
        self.session.close()
    
    def __enter__(self):
        """Контекстный менеджер"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие сессии"""
        self.close()
