"""
Менеджер для управления процессом веб-скрапинга

Предоставляет функциональность для:
- Управления множественными загрузками
- Мониторинга прогресса
- Сохранения метаданных
- Экспорта результатов
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from .html_downloader import HTMLDownloader
import logging

logger = logging.getLogger(__name__)


class ScrapingManager:
    """Менеджер для управления процессом веб-скрапинга"""
    
    def __init__(self, 
                 base_url: str,
                 save_path: str = "./scraping_results",
                 metadata_file: str = "scraping_metadata.json"):
        """
        Инициализация менеджера скрапинга
        
        Args:
            base_url: Базовый URL для скрапинга
            save_path: Путь для сохранения результатов
            metadata_file: Имя файла с метаданными
        """
        self.base_url = base_url
        self.save_path = Path(save_path)
        self.metadata_file = self.save_path / metadata_file
        
        # Создаём папки
        self.save_path.mkdir(parents=True, exist_ok=True)
        
        # Метаданные скрапинга
        self.metadata = {
            'base_url': base_url,
            'created_at': datetime.now().isoformat(),
            'sessions': []
        }
        
        # Загружаем существующие метаданные если есть
        self._load_metadata()
    
    def start_scraping_session(self, 
                              session_name: str,
                              num_pages: int,
                              delay_range: tuple = (1, 5),
                              filename_pattern: str = "page_{}.html") -> Dict[str, Any]:
        """
        Начинает новую сессию скрапинга
        
        Args:
            session_name: Название сессии
            num_pages: Количество страниц для загрузки
            delay_range: Диапазон задержек между запросами
            filename_pattern: Шаблон для имён файлов
            
        Returns:
            Результаты сессии
        """
        logger.info(f"Начинаю сессию скрапинга: {session_name}")
        
        session_data = {
            'name': session_name,
            'started_at': datetime.now().isoformat(),
            'num_pages': num_pages,
            'delay_range': delay_range,
            'filename_pattern': filename_pattern,
            'results': []
        }
        
        # Создаём загрузчик для этой сессии
        session_save_path = self.save_path / session_name
        downloader = HTMLDownloader(
            base_url=self.base_url,
            save_path=str(session_save_path),
            delay_range=delay_range
        )
        
        try:
            # Загружаем страницы
            downloaded_files = downloader.download_multiple_pages(
                num_pages=num_pages,
                filename_pattern=filename_pattern,
                delay=True
            )
            
            # Получаем статистику
            stats = downloader.get_stats()
            
            # Сохраняем результаты сессии
            session_data.update({
                'completed_at': datetime.now().isoformat(),
                'downloaded_files': downloaded_files,
                'stats': stats,
                'status': 'completed'
            })
            
            logger.info(f"Сессия {session_name} завершена успешно")
            
        except Exception as e:
            logger.error(f"Ошибка в сессии {session_name}: {e}")
            session_data.update({
                'completed_at': datetime.now().isoformat(),
                'error': str(e),
                'status': 'failed'
            })
        
        finally:
            downloader.close()
        
        # Добавляем сессию в метаданные
        self.metadata['sessions'].append(session_data)
        self._save_metadata()
        
        return session_data
    
    def scrape_with_parameters(self, 
                              session_name: str,
                              parameters_list: List[Dict[str, Any]],
                              delay_range: tuple = (1, 3)) -> Dict[str, Any]:
        """
        Скрапинг с различными параметрами запроса
        
        Args:
            session_name: Название сессии
            parameters_list: Список параметров для запросов
            delay_range: Диапазон задержек между запросами
            
        Returns:
            Результаты сессии
        """
        logger.info(f"Начинаю скрапинг с параметрами: {session_name}")
        
        session_data = {
            'name': session_name,
            'started_at': datetime.now().isoformat(),
            'type': 'parameter_based',
            'parameters_count': len(parameters_list),
            'delay_range': delay_range,
            'results': []
        }
        
        # Создаём загрузчик
        session_save_path = self.save_path / session_name
        downloader = HTMLDownloader(
            base_url=self.base_url,
            save_path=str(session_save_path),
            delay_range=delay_range
        )
        
        try:
            for i, params in enumerate(parameters_list):
                filename = f"params_{i+1}.html"
                
                if downloader.download_with_parameters(params, filename):
                    session_data['results'].append({
                        'params': params,
                        'filename': filename,
                        'status': 'success'
                    })
                else:
                    session_data['results'].append({
                        'params': params,
                        'filename': filename,
                        'status': 'failed'
                    })
                
                # Задержка между запросами
                if i < len(parameters_list) - 1:
                    import time
                    import random
                    sleep_time = random.uniform(*delay_range)
                    logger.info(f"Ожидание {sleep_time:.2f} секунд...")
                    time.sleep(sleep_time)
            
            session_data.update({
                'completed_at': datetime.now().isoformat(),
                'status': 'completed'
            })
            
        except Exception as e:
            logger.error(f"Ошибка в сессии {session_name}: {e}")
            session_data.update({
                'completed_at': datetime.now().isoformat(),
                'error': str(e),
                'status': 'failed'
            })
        
        finally:
            downloader.close()
        
        # Добавляем сессию в метаданные
        self.metadata['sessions'].append(session_data)
        self._save_metadata()
        
        return session_data
    
    def get_session_summary(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        Получает сводку по конкретной сессии
        
        Args:
            session_name: Название сессии
            
        Returns:
            Данные сессии или None если не найдена
        """
        for session in self.metadata['sessions']:
            if session['name'] == session_name:
                return session
        return None
    
    def get_all_sessions_summary(self) -> List[Dict[str, Any]]:
        """
        Получает сводку по всем сессиям
        
        Returns:
            Список сводок по сессиям
        """
        summary = []
        
        for session in self.metadata['sessions']:
            session_summary = {
                'name': session['name'],
                'started_at': session['started_at'],
                'status': session['status'],
                'type': session.get('type', 'standard')
            }
            
            if 'completed_at' in session:
                session_summary['completed_at'] = session['completed_at']
            
            if 'stats' in session:
                session_summary['stats'] = session['stats']
            
            summary.append(session_summary)
        
        return summary
    
    def export_metadata_to_csv(self, filename: str = "scraping_summary.csv"):
        """
        Экспортирует метаданные в CSV файл
        
        Args:
            filename: Имя CSV файла
        """
        csv_path = self.save_path / filename
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['session_name', 'started_at', 'completed_at', 'status', 'type', 'success_rate']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for session in self.metadata['sessions']:
                row = {
                    'session_name': session['name'],
                    'started_at': session['started_at'],
                    'completed_at': session.get('completed_at', ''),
                    'status': session['status'],
                    'type': session.get('type', 'standard'),
                    'success_rate': session.get('stats', {}).get('success_rate_percent', 0)
                }
                writer.writerow(row)
        
        logger.info(f"Метаданные экспортированы в {csv_path}")
    
    def _load_metadata(self):
        """Загружает существующие метаданные"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    existing_metadata = json.load(f)
                    # Обновляем базовые поля, сохраняем сессии
                    self.metadata.update(existing_metadata)
                    if 'sessions' in existing_metadata:
                        self.metadata['sessions'] = existing_metadata['sessions']
                logger.info("Метаданные загружены")
            except Exception as e:
                logger.warning(f"Не удалось загрузить метаданные: {e}")
    
    def _save_metadata(self):
        """Сохраняет метаданные в файл"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Не удалось сохранить метаданные: {e}")
    
    def get_total_stats(self) -> Dict[str, Any]:
        """
        Получает общую статистику по всем сессиям
        
        Returns:
            Общая статистика
        """
        total_sessions = len(self.metadata['sessions'])
        completed_sessions = sum(1 for s in self.metadata['sessions'] if s['status'] == 'completed')
        failed_sessions = sum(1 for s in self.metadata['sessions'] if s['status'] == 'failed')
        
        total_files = 0
        total_success_rate = 0
        
        for session in self.metadata['sessions']:
            if 'stats' in session and 'successful' in session['stats']:
                total_files += session['stats']['successful']
                total_success_rate += session['stats'].get('success_rate_percent', 0)
        
        avg_success_rate = total_success_rate / completed_sessions if completed_sessions > 0 else 0
        
        return {
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'failed_sessions': failed_sessions,
            'total_downloaded_files': total_files,
            'average_success_rate': round(avg_success_rate, 2),
            'last_updated': datetime.now().isoformat()
        }
