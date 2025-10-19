#!/usr/bin/env python3
"""
Модуль для парсинга страницы с тестами на practicatest.com

Предоставляет функционал для:
- Навигации по страницам сайта
- Поиска и нажатия кнопок
- Извлечения данных из таблиц
- Обработки результатов
"""

import logging
import time
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)


class PracticaTestParser:
    """Класс для парсинга страниц practicatest.com"""
    
    def __init__(self, auth_session):
        """
        Инициализация парсера
        
        Args:
            auth_session: Сессия requests с авторизацией
        """
        self.session = auth_session
        self.base_url = "https://practicatest.com"
        self.tests_url = "https://practicatest.com/tests/permiso-B"
        self.current_modal = None
        
        logger.info("Парсер practicatest.com инициализирован")
    
    def navigate_to_tests_page(self) -> bool:
        """
        Переходит на страницу с тестами
        
        Returns:
            True если переход успешен
        """
        try:
            logger.info("Перехожу на страницу с тестами...")
            response = self.session.get(self.tests_url, timeout=30)
            response.raise_for_status()
            
            if response.status_code == 200:
                logger.info("✅ Страница с тестами загружена")
                return True
            else:
                logger.error(f"❌ Ошибка загрузки страницы: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при переходе на страницу тестов: {e}")
            return False
    
    def find_test_section(self) -> Optional[BeautifulSoup]:
        """
        Находит раздел "Test del Permiso B" на странице
        
        Returns:
            BeautifulSoup объект раздела или None
        """
        try:
            logger.info("Ищу раздел 'Test del Permiso B'...")
            response = self.session.get(self.tests_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем заголовок "Test del Permiso B"
            test_section = soup.find('h2', string=lambda text: text and 'Test del Permiso B' in text)
            
            if test_section:
                logger.info("✅ Раздел 'Test del Permiso B' найден")
                return test_section
            else:
                # Попробуем найти по другому селектору
                test_section = soup.find('h2', class_=lambda x: x and 'test' in x.lower())
                if test_section:
                    logger.info("✅ Раздел с тестами найден по классу")
                    return test_section
                
                logger.warning("⚠️ Раздел 'Test del Permiso B' не найден")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске раздела тестов: {e}")
            return None
    
    def find_ver_los_test_button(self) -> Optional[BeautifulSoup]:
        """
        Находит кнопку "VER LOS TEST"
        
        Returns:
            BeautifulSoup объект кнопки или None
        """
        try:
            logger.info("Ищу кнопку 'VER LOS TEST'...")
            response = self.session.get(self.tests_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем кнопку по тексту
            button = soup.find('button', string=lambda text: text and 'VER LOS TEST' in text)
            
            if button:
                logger.info("✅ Кнопка 'VER LOS TEST' найдена")
                return button
            
            # Попробуем найти по ссылке
            link = soup.find('a', string=lambda text: text and 'VER LOS TEST' in text)
            if link:
                logger.info("✅ Ссылка 'VER LOS TEST' найдена")
                return link
            
            # Попробуем найти по частичному совпадению
            button = soup.find('button', string=lambda text: text and 'TEST' in text.upper())
            if button:
                logger.info("✅ Кнопка с 'TEST' найдена")
                return button
            
            logger.warning("⚠️ Кнопка 'VER LOS TEST' не найдена")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске кнопки: {e}")
            return None
    
    def click_ver_los_test(self) -> bool:
        """
        Нажимает кнопку "VER LOS TEST" и получает модальное окно с таблицей
        
        Returns:
            True если модальное окно получено
        """
        try:
            logger.info("Нажимаю кнопку 'VER LOS TEST'...")
            
            # Сначала находим кнопку
            button = self.find_ver_los_test_button()
            if not button:
                logger.error("❌ Кнопка не найдена")
                return False
            
            # Проверяем, что это модальная кнопка
            modal_target = button.get('data-bs-target')
            if modal_target:
                logger.info(f"✅ Найдена модальная кнопка с target: {modal_target}")
                
                # Получаем страницу с модальным окном
                response = self.session.get(self.tests_url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Ищем модальное окно
                modal = soup.find('div', id=modal_target.lstrip('#'))
                if modal:
                    logger.info("✅ Модальное окно найдено")
                    # Сохраняем модальное окно для дальнейшего использования
                    self.current_modal = modal
                    return True
                else:
                    logger.warning("⚠️ Модальное окно не найдено")
                    return False
            
            # Если это ссылка, получаем её URL
            elif button.name == 'a':
                href = button.get('href')
                if href:
                    if href.startswith('/'):
                        url = self.base_url + href
                    else:
                        url = href
                    
                    logger.info(f"Перехожу по ссылке: {url}")
                    response = self.session.get(url, timeout=30)
                    response.raise_for_status()
                    
                    if response.status_code == 200:
                        logger.info("✅ Переход по ссылке успешен")
                        return True
                    else:
                        logger.error(f"❌ Ошибка перехода: {response.status_code}")
                        return False
            
            # Если это обычная кнопка, попробуем найти форму
            elif button.name == 'button':
                form = button.find_parent('form')
                if form:
                    action = form.get('action')
                    if action:
                        if action.startswith('/'):
                            url = self.base_url + action
                        else:
                            url = action
                        
                        logger.info(f"Отправляю форму: {url}")
                        response = self.session.post(url, timeout=30)
                        response.raise_for_status()
                        
                        if response.status_code == 200:
                            logger.info("✅ Отправка формы успешна")
                            return True
                        else:
                            logger.error(f"❌ Ошибка отправки формы: {response.status_code}")
                            return False
                
                logger.warning("⚠️ Не удалось определить действие для кнопки")
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка при нажатии кнопки: {e}")
            return False
    
    def get_tests_table(self) -> Optional[BeautifulSoup]:
        """
        Получает таблицу с доступными тестами
        
        Returns:
            BeautifulSoup объект таблицы или None
        """
        try:
            logger.info("Получаю таблицу с тестами...")
            
            # Сначала переходим на страницу с тестами
            if not self.navigate_to_tests_page():
                return None
            
            # Нажимаем кнопку "VER LOS TEST" и получаем модальное окно
            if not self.click_ver_los_test():
                return None
            
            # Если у нас есть модальное окно, ищем в нём таблицу
            if self.current_modal:
                logger.info("Ищу таблицу в модальном окне...")
                
                # Ищем таблицу в модальном окне
                table = self.current_modal.find('table')
                if table:
                    logger.info("✅ Таблица с тестами найдена в модальном окне")
                    return table
                
                # Если таблица не найдена, ищем список тестов
                tests_list = self.current_modal.find('ul') or self.current_modal.find('div', class_=lambda x: x and 'test' in x.lower())
                if tests_list:
                    logger.info("✅ Список тестов найден в модальном окне")
                    return tests_list
                
                # Ищем любые элементы с тестами
                test_elements = self.current_modal.find_all(['div', 'li'], class_=lambda x: x and any(word in x.lower() for word in ['test', 'examen', 'dia']))
                if test_elements:
                    logger.info(f"✅ Найдено {len(test_elements)} элементов с тестами в модальном окне")
                    return test_elements[0].parent  # Возвращаем родительский контейнер
            
            logger.warning("⚠️ Таблица или список тестов не найден")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении таблицы тестов: {e}")
            return None
    
    def parse_tests_data(self) -> List[Dict[str, Any]]:
        """
        Парсит данные из таблицы тестов
        
        Returns:
            Список словарей с данными тестов
        """
        try:
            logger.info("Парсинг данных из таблицы тестов...")
            
            table = self.get_tests_table()
            if not table:
                logger.error("❌ Таблица не найдена")
                return []
            
            tests_data = []
            
            # Если это таблица
            if table.name == 'table':
                rows = table.find_all('tr')
                for row in rows[1:]:  # Пропускаем заголовок
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        test_info = {
                            'date': cells[0].get_text(strip=True) if len(cells) > 0 else '',
                            'status': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                            'action': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                            'raw_html': str(row)
                        }
                        tests_data.append(test_info)
            
            # Если это список
            elif table.name in ['ul', 'div']:
                items = table.find_all(['li', 'div'])
                for item in items:
                    text = item.get_text(strip=True)
                    if text and ('test' in text.lower() or 'examen' in text.lower()):
                        test_info = {
                            'text': text,
                            'raw_html': str(item)
                        }
                        tests_data.append(test_info)
            
            logger.info(f"✅ Найдено {len(tests_data)} тестов")
            return tests_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка при парсинге данных: {e}")
            return []
    
    def get_page_content(self, url: str = None) -> Optional[str]:
        """
        Получает содержимое страницы
        
        Args:
            url: URL страницы (если не указан, используется tests_url)
            
        Returns:
            HTML содержимое страницы или None
        """
        try:
            if not url:
                url = self.tests_url
            
            logger.info(f"Получаю содержимое страницы: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            return response.text
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении содержимого страницы: {e}")
            return None
    
    def debug_page_structure(self) -> Dict[str, Any]:
        """
        Анализирует структуру текущей страницы для отладки
        
        Returns:
            Словарь с информацией о структуре страницы
        """
        try:
            logger.info("Анализирую структуру страницы...")
            
            response = self.session.get(self.tests_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Анализируем заголовки
            headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            header_texts = [h.get_text(strip=True) for h in headers if h.get_text(strip=True)]
            
            # Анализируем кнопки
            buttons = soup.find_all('button')
            button_texts = [b.get_text(strip=True) for b in buttons if b.get_text(strip=True)]
            
            # Анализируем ссылки
            links = soup.find_all('a')
            link_texts = [a.get_text(strip=True) for a in links if a.get_text(strip=True)]
            
            # Анализируем таблицы
            tables = soup.find_all('table')
            
            # Анализируем формы
            forms = soup.find_all('form')
            
            # Анализируем модальные окна
            modals = soup.find_all('div', class_=lambda x: x and 'modal' in x.lower())
            
            debug_info = {
                'url': self.tests_url,
                'title': soup.title.get_text(strip=True) if soup.title else '',
                'headers': header_texts,
                'buttons': button_texts,
                'links': link_texts,
                'tables_count': len(tables),
                'forms_count': len(forms),
                'modals_count': len(modals),
                'page_size': len(response.content)
            }
            
            logger.info("✅ Анализ структуры страницы завершён")
            return debug_info
            
        except Exception as e:
            logger.error(f"❌ Ошибка при анализе структуры страницы: {e}")
            return {}
