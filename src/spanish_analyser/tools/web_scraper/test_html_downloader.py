"""
Тесты для класса HTMLDownloader
"""

import unittest
from unittest.mock import patch, Mock
import tempfile
import os
from pathlib import Path
import sys

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from html_downloader import HTMLDownloader


class TestHTMLDownloader(unittest.TestCase):
    """Тесты для класса HTMLDownloader"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.temp_dir = tempfile.mkdtemp()
        self.downloader = HTMLDownloader(
            base_url="https://example.com",
            save_path=self.temp_dir
        )
    
    def tearDown(self):
        """Очистка после каждого теста"""
        self.downloader.close()
        # Удаляем временную папку
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('requests.Session')
    def test_init(self, mock_session):
        """Тест инициализации загрузчика"""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        
        downloader = HTMLDownloader(
            base_url="https://test.com",
            save_path="./test_path",
            delay_range=(2, 5),
            max_retries=5
        )
        
        self.assertEqual(downloader.base_url, "https://test.com")
        self.assertEqual(downloader.delay_range, (2, 5))
        self.assertEqual(downloader.max_retries, 5)
        self.assertEqual(downloader.save_path, Path("./test_path"))
        
        # Проверяем, что папка создана
        self.assertTrue(Path("./test_path").exists())
        
        # Очистка
        downloader.close()
        import shutil
        if Path("./test_path").exists():
            shutil.rmtree("./test_path")
    
    @patch('requests.Session')
    def test_download_page_success(self, mock_session):
        """Тест успешной загрузки страницы"""
        # Мокаем успешный ответ
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        # Создаём новый загрузчик с моком
        downloader = HTMLDownloader(
            base_url="https://example.com",
            save_path=self.temp_dir
        )
        
        # Загружаем страницу
        result = downloader.download_page(filename="test.html")
        
        self.assertTrue(result)
        self.assertEqual(downloader.download_stats['successful'], 1)
        self.assertEqual(downloader.download_stats['total_requests'], 1)
        
        # Проверяем, что файл создан
        file_path = Path(self.temp_dir) / "test.html"
        self.assertTrue(file_path.exists())
        
        # Проверяем содержимое файла
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertEqual(content, "<html><body>Test content</body></html>")
        
        downloader.close()
    
    @patch('requests.Session')
    def test_download_page_failure(self, mock_session):
        """Тест неудачной загрузки страницы"""
        # Мокаем неудачный ответ
        mock_response = Mock()
        mock_response.status_code = 404
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        downloader = HTMLDownloader(
            base_url="https://example.com",
            save_path=self.temp_dir
        )
        
        # Загружаем страницу
        result = downloader.download_page(filename="test.html")
        
        self.assertFalse(result)
        self.assertEqual(downloader.download_stats['failed'], 1)
        self.assertEqual(downloader.download_stats['total_requests'], 1)
        
        downloader.close()
    
    @patch('requests.Session')
    def test_download_multiple_pages(self, mock_session):
        """Тест загрузки нескольких страниц"""
        # Мокаем успешные ответы
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Test</html>"
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        downloader = HTMLDownloader(
            base_url="https://example.com",
            save_path=self.temp_dir
        )
        
        # Загружаем 3 страницы
        downloaded_files = downloader.download_multiple_pages(
            num_pages=3,
            filename_pattern="page_{}.html"
        )
        
        self.assertEqual(len(downloaded_files), 3)
        self.assertEqual(downloader.download_stats['successful'], 3)
        self.assertEqual(downloader.download_stats['total_requests'], 3)
        
        # Проверяем, что файлы созданы
        for i in range(1, 4):
            file_path = Path(self.temp_dir) / f"page_{i}.html"
            self.assertTrue(file_path.exists())
        
        downloader.close()
    
    def test_generate_filename(self):
        """Тест генерации имени файла"""
        # Тест с обычным URL
        filename = self.downloader._generate_filename("https://example.com/page")
        self.assertIn("example_com", filename)
        self.assertIn("page", filename)
        self.assertTrue(filename.endswith(".html"))
        
        # Тест с URL без пути
        filename = self.downloader._generate_filename("https://example.com")
        self.assertIn("example_com", filename)
        self.assertIn("index", filename)
        self.assertTrue(filename.endswith(".html"))
    
    def test_get_stats(self):
        """Тест получения статистики"""
        # Устанавливаем тестовые данные
        self.downloader.download_stats = {
            'successful': 5,
            'failed': 2,
            'total_requests': 7
        }
        
        stats = self.downloader.get_stats()
        
        self.assertEqual(stats['successful'], 5)
        self.assertEqual(stats['failed'], 2)
        self.assertEqual(stats['total_requests'], 7)
        self.assertEqual(stats['success_rate_percent'], 71.43)  # 5/7 * 100
        self.assertEqual(stats['save_path'], self.temp_dir)
    
    def test_clear_stats(self):
        """Тест сброса статистики"""
        # Устанавливаем тестовые данные
        self.downloader.download_stats = {
            'successful': 5,
            'failed': 2,
            'total_requests': 7
        }
        
        # Сбрасываем статистику
        self.downloader.clear_stats()
        
        # Проверяем, что статистика сброшена
        expected_stats = {
            'successful': 0,
            'failed': 0,
            'total_requests': 0
        }
        self.assertEqual(self.downloader.download_stats, expected_stats)
    
    def test_context_manager(self):
        """Тест контекстного менеджера"""
        with HTMLDownloader(
            base_url="https://example.com",
            save_path=self.temp_dir
        ) as downloader:
            self.assertIsNotNone(downloader)
            self.assertIsNotNone(downloader.session)
        
        # После выхода из контекста сессия должна быть закрыта
        # (проверяем через мок в реальных тестах)


if __name__ == "__main__":
    unittest.main()
