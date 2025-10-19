#!/usr/bin/env python3
"""
Анализатор билетов по вождению

Анализирует HTML файлы с билетами и создаёт Excel отчёты
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import time

# Добавляем путь к модулям проекта
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from spanish_analyser.word_analyzer import WordAnalyzer
from spanish_analyser.config import config
from spanish_analyser.anki_checker import check_anki_before_run
from spanish_analyser.cache import CacheManager  # Менеджер с поддержкой подпапок
from spanish_analyser.components.word_comparator import WordComparator
from spanish_analyser.components.anki_connector import AnkiConnector


class DrivingTestsAnalyzer:
    """Анализатор билетов по вождению"""
    
    def __init__(self):
        """Инициализация анализатора"""
        self.word_analyzer = WordAnalyzer()
        
        # Получаем настройки из конфигурации
        self.downloads_path = Path(config.get_downloads_folder())
        self.results_path = Path(config.get_results_folder())
        self.max_results_files = config.get_max_results_files()
        self.results_filename_prefix = config.get_results_filename_prefix()
        
        # Создаём папку для результатов
        self.results_path.mkdir(parents=True, exist_ok=True)
        
        # Инициализируем компоненты
        from spanish_analyser.text_processor import SpanishTextProcessor
        self.text_processor = SpanishTextProcessor()
        
        # Статистика анализа
        self.analysis_stats = {
            'files_processed': 0,
            'words_found': 0,
            'start_time': datetime.now()
        }
        
        # Используем централизованную настройку логирования из config
        # (не переопределяем, если уже настроено в CLI)
        config._configure_logging_if_needed()
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Анализатор инициализирован")
        self.logger.info(f"Папка загрузок: {self.downloads_path}")
        self.logger.info(f"Папка результатов: {self.results_path}")
    
    def connect_to_anki(self) -> bool:
        """
        Инициализирует известные слова через AnkiConnect (без прямого доступа к БД Anki).
        
        Returns:
            True если загрузка успешна
        """
        try:
            self.logger.info("Подключаюсь к Anki через AnkiConnect...")
            connector = AnkiConnector()
            if not connector.is_available():
                self.logger.warning("⚠️ AnkiConnect недоступен. Продолжаю без Anki")
                return False

            # Инициализируем современную интеграцию с ANKI в WordAnalyzer
            if self.word_analyzer.init_anki_integration():
                self.logger.info("✅ WordAnalyzer настроен для работы с ANKI (AnkiConnect)")
                return True
            else:
                self.logger.warning("⚠️ Не удалось инициализировать интеграцию с ANKI")
                return False
        except Exception as e:
            self.logger.error(f"❌ Ошибка при загрузке слов из Anki (AnkiConnect): {e}")
            return False
    
    def find_html_files(self, pattern: str = "*.html") -> list:
        """
        Находит HTML файлы для анализа
        
        Args:
            pattern: Паттерн для поиска файлов
            
        Returns:
            Список путей к HTML файлам
        """
        html_files = list(self.downloads_path.glob(pattern))
        self.logger.info(f"Найдено {len(html_files)} HTML файлов для анализа")
        return html_files
    
    def extract_text_from_html(self, html_file: Path) -> str:
        """
        Извлекает текст из HTML файла
        
        Args:
            html_file: Путь к HTML файлу
            
        Returns:
            Извлечённый текст
        """
        try:
            # Попытка получить из кэша по пути и времени модификации
            if config.should_cache_html_extraction():
                try:
                    stat = html_file.stat()
                    cache_key = f"html_extract:{str(html_file.resolve())}:{stat.st_mtime}:{stat.st_size}"
                    cache = CacheManager.get_cache()
                    cached = cache.get(cache_key)
                    if cached is not None:
                        self.logger.info(f"📄 Кэш: {html_file.name} ({len(cached)} символов)")
                        return cached
                except Exception:
                    pass
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Используем улучшенный метод извлечения текста
            cleaned_text = self._extract_text_improved(html_content)
            
            # Дополнительно извлекаем испанские слова для лучшего качества
            spanish_words = self.text_processor.extract_spanish_words(cleaned_text)
            
            # Объединяем в текст для анализа
            final_text = ' '.join(spanish_words)
            
            self.logger.debug(f"Извлечён текст из {html_file.name}: {len(final_text)} символов, {len(spanish_words)} слов")

            # Сохраняем в кэш
            if config.should_cache_html_extraction():
                try:
                    cache.set(cache_key, final_text)
                    self.logger.debug(f"💾 Текст кэширован: {html_file.name}")
                except Exception:
                    pass
            return final_text
            
        except Exception as e:
            self.logger.error(f"Ошибка при извлечении текста из {html_file.name}: {e}")
            return ""
    
    def _extract_text_improved(self, html_content: str) -> str:
        """
        Улучшенное извлечение текста из HTML с поиском блоков col-md-8
        
        Args:
            html_content: HTML содержимое
            
        Returns:
            Извлечённый текст
        """
        try:
            from bs4 import BeautifulSoup
            
            # Создаём объект BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Извлекаем все блоки с классом "col-md-8" (как в оригинальном коде)
            blocks = soup.find_all('div', class_='col-md-8')
            
            if blocks:
                # Извлекаем текст из каждого блока и объединяем их
                block_texts = []
                for block in blocks:
                    # Используем простой и надёжный метод извлечения текста
                    block_text = block.get_text(separator=" ", strip=True)
                    if block_text and len(block_text) > 10:  # Исключаем слишком короткие блоки
                        block_texts.append(block_text)
                
                text = "\n".join(block_texts)
                self.logger.debug(f"Найдено {len(blocks)} блоков col-md-8")
            else:
                raise RuntimeError("Не найден основной контент (col-md-8) в HTML. Операция недоступна из-за отсутствия нужной структуры.")
            
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"Ошибка при улучшенном извлечении текста: {e}")
            raise
    
    def _extract_text_from_element(self, element) -> str:
        """
        Надёжно извлекает текст из HTML элемента
        
        Args:
            element: HTML элемент BeautifulSoup
            
        Returns:
            Извлечённый текст
        """
        try:
            # Метод 1: Прямое извлечение текста
            text = element.get_text(separator=" ", strip=True)
            
            # Метод 2: Если текст слишком короткий, пробуем извлечь по частям
            if len(text) < 10:  # Подозрительно короткий текст
                # Извлекаем текст из всех дочерних элементов
                child_texts = []
                for child in element.children:
                    if hasattr(child, 'get_text'):
                        child_text = child.get_text(strip=True)
                        if child_text:
                            child_texts.append(child_text)
                    elif hasattr(child, 'string') and child.string:
                        child_text = child.string.strip()
                        if child_text:
                            child_texts.append(child_text)
                
                if child_texts:
                    text = " ".join(child_texts)
            
            # Метод 3: Если всё ещё короткий, пробуем извлечь атрибуты
            if len(text) < 10:
                # Ищем текст в атрибутах
                for attr_name, attr_value in element.attrs.items():
                    if isinstance(attr_value, str) and len(attr_value) > len(text):
                        text = attr_value
            
            return text.strip()
            
        except Exception as e:
            self.logger.warning(f"Ошибка при извлечении текста из элемента: {e}")
            return ""
    
    def analyze_html_files(self, html_files: list = None) -> dict:
        """
        Анализирует HTML файлы и извлекает слова
        
        Args:
            html_files: Список HTML файлов для анализа
            
        Returns:
            Словарь со статистикой анализа
        """
        if html_files is None:
            html_files = self.find_html_files()
        
        self.logger.info(f"Начинаю анализ {len(html_files)} HTML файлов")
        
        total_words = 0
        
        for html_file in html_files:
            try:
                t_file_start = time.time()
                self.logger.debug(f"➡️ Обработка файла: {html_file.name}")
                # Извлекаем текст
                text = self.extract_text_from_html(html_file)
                if text:
                    self.logger.debug(f"➡️ spaCy-анализ файла {html_file.name}: {len(text)} символов")
                    # Добавляем слова в анализатор
                    self.word_analyzer.add_words_from_text(text)
                    
                    # Подсчитываем слова в этом файле
                    words_in_file = len(text.split())
                    total_words += words_in_file
                    
                    self.analysis_stats['files_processed'] += 1
                    self.logger.info(f"✅ Обработан {html_file.name}: найдено {words_in_file} слов (dt={time.time()-t_file_start:.2f}s)")
                else:
                    self.logger.warning(f"⚠️ Пропущен {html_file.name}: пустой текст")
                    
            except Exception as e:
                self.logger.error(f"❌ Ошибка при анализе {html_file.name}: {e}")
        
        self.analysis_stats['words_found'] = total_words
        
        self.logger.info(f"Анализ завершён. Обработано файлов: {self.analysis_stats['files_processed']}")
        self.logger.info(f"Всего найдено слов: {total_words}")
        
        return {
            'files_processed': self.analysis_stats['files_processed'],
            'words_found': total_words,
            'unique_words': len(self.word_analyzer.word_frequencies)
        }
    
    def generate_filename_with_timestamp(self, prefix: str = "driving_tests_analysis") -> str:
        """
        Генерирует имя файла с временной меткой
        
        Args:
            prefix: Префикс для имени файла
            
        Returns:
            Имя файла с временной меткой
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.xlsx"
    
    def cleanup_old_files(self):
        """Удаляет старые файлы результатов, оставляя не более max_files"""
        try:
            # Находим все Excel файлы в папке результатов
            excel_files = list(self.results_path.glob("*.xlsx"))
            
            if len(excel_files) > self.max_results_files:
                # Сортируем по времени изменения (старые первыми)
                excel_files.sort(key=lambda x: x.stat().st_mtime)
                
                # Удаляем самые старые файлы
                files_to_delete = excel_files[:-self.max_results_files]
                
                for old_file in files_to_delete:
                    old_file.unlink()
                    self.logger.info(f"Удалён старый файл: {old_file.name}")
                
                self.logger.info(f"Удалено {len(files_to_delete)} старых файлов результатов")
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке старых файлов: {e}")
    
    def export_results(self, include_categories: bool = True) -> str:
        """
        Экспортирует результаты анализа в Excel
        
        Args:
            include_categories: Включать ли категории по частоте
            
        Returns:
            Путь к созданному файлу
        """
        try:
            # Генерируем имя файла с временной меткой
            filename = self.generate_filename_with_timestamp("driving_tests_analysis")
            file_path = self.results_path / filename
            
            # Экспортируем результаты
            self.word_analyzer.export_to_excel(str(file_path), include_categories)
            
            # Очищаем старые файлы
            self.cleanup_old_files()
            
            self.logger.info(f"Результаты экспортированы в: {filename}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Ошибка при экспорте результатов: {e}")
            return ""
    
    
    def reset_analysis(self):
        """Сбрасывает результаты анализа"""
        self.word_analyzer.reset()
        self.analysis_stats = {
            'files_processed': 0,
            'words_found': 0,
            'start_time': datetime.now()
        }
        self.logger.info("Результаты анализа сброшены")
    
    def close(self):
        """Завершение работы анализатора (соединений с Anki нет)."""
        pass


def main():
    """Основная функция для демонстрации"""
    print("📊 Анализатор билетов по вождению\n")
    
    # Информационная проверка AnkiConnect (не требуем закрывать Anki)
    print("🔍 Проверка доступности AnkiConnect...")
    try:
        _conn = AnkiConnector()
        if _conn.is_available():
            decks = _conn.find_spanish_decks("Spanish")
            print(f"✅ AnkiConnect доступен. Испанских колод: {len(decks)}")
        else:
            print("⚠️ AnkiConnect недоступен. Будем работать без Anki")
    except Exception:
        print("⚠️ AnkiConnect недоступен. Будем работать без Anki")
    
    # Создаём анализатор
    analyzer = DrivingTestsAnalyzer()
    
    try:
        # Подключаемся к Anki
        print("🔗 Подключение к Anki...")
        if not analyzer.connect_to_anki():
            print("⚠️ Продолжаю без Anki...")
        
        # Анализируем HTML файлы
        print("\n📄 Начинаю анализ HTML файлов...")
        analysis_result = analyzer.analyze_html_files()
        
        print(f"\n📊 Результаты анализа:")
        print(f"   Обработано файлов: {analysis_result['files_processed']}")
        print(f"   Найдено слов: {analysis_result['words_found']}")
        print(f"   Уникальных слов: {analysis_result['unique_words']}")
        
        # Экспортируем результаты
        print(f"\n📁 Экспортирую результаты...")
        export_file = analyzer.export_results()
        
        if export_file:
            print(f"✅ Результаты экспортированы в: {export_file}")
        
        
        # Показываем статистику кэша
        try:
            from spanish_analyser.cache import CacheManager  # Менеджер с поддержкой подпапок
            cache = CacheManager.get_cache()
            cache_stats = cache.stats_dict()
            if cache_stats['hits'] > 0 or cache_stats['stores'] > 0:
                print(f"\n💾 Статистика кэша:")
                print(f"   Попаданий: {cache_stats['hits']}")
                print(f"   Промахов: {cache_stats['misses']}")
                print(f"   Файлов в кэше: {cache_stats['files']}")
                print(f"   Размер кэша: {cache_stats['size_mb']:.1f} МБ")
        except Exception:
            pass
        
    except Exception as e:
        print(f"\n❌ Произошла ошибка: {e}")
        return 1
    finally:
        analyzer.close()
    
    return 0


if __name__ == "__main__":
    exit(main())
