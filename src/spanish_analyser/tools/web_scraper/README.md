# Web Scraper - Универсальный веб-скрапинг

Универсальный инструмент для веб-скрапинга с поддержкой авторизации, специализированный для работы с сайтом practicatest.com.

## 🚀 Возможности

### Основные функции
- **HTML Downloader** - Базовый загрузчик HTML страниц с retry логикой
- **Scraping Manager** - Менеджер скрапинга с метаданными и отчётами
- **Driving Tests Downloader** - Специализация для билетов по вождению
- **PracticaTest Auth** - Модуль авторизации для practicatest.com
- **PracticaTest Parser** - Парсер для извлечения данных с practicatest.com
- **Test Downloader** - Загрузчик тестов по датам с проверкой существующих файлов

### Специализированные возможности
- Авторизация на practicatest.com
- Анализ таблицы доступных тестов
- Автоматическая загрузка новых тестов
- Проверка уже загруженных тестов
- Очистка HTML от изображений и лишнего контента
- Форматирование названий файлов по датам

## 🏗️ Архитектура

```
web_scraper/
├── html_downloader.py           # Базовый загрузчик HTML
├── scraping_manager.py          # Менеджер скрапинга
├── driving_tests_downloader.py # Специализация для билетов
├── practicatest_auth.py        # Модуль авторизации
├── practicatest_parser.py      # Парсер страниц
├── test_downloader.py          # Загрузчик тестов по датам (ядро)
├── download_tests.py           # Основной CLI-скрипт загрузки
└── examples/                   # Примеры/демо-скрипты (были test_*.py)
```

## 🚀 Быстрый старт

### 1. Настройка авторизации

Создайте файл `.env` в корневой папке проекта:

```bash
# Конфигурация для авторизации на practicatest.com
PRACTICATEST_EMAIL=ваш_email@example.com
PRACTICATEST_PASSWORD=ваш_пароль_здесь

# Настройки загрузки
DOWNLOAD_DELAY_MIN=3
DOWNLOAD_DELAY_MAX=7
LOGIN_DELAY=2
SESSION_TIMEOUT=3600
MAX_RETRIES=3
```

### 2. Загрузка тестов

```bash
# Запуск основного скрипта загрузки
python download_tests.py
```

### 3. Программное использование

```python
from practicatest_auth import PracticaTestAuth
from practicatest_parser import PracticaTestParser
from test_downloader import TestDownloader

# Авторизация
auth = PracticaTestAuth()
auth.login()

# Создание парсера и загрузчика
parser = PracticaTestParser(auth.session)
downloader = TestDownloader(auth.session)

# Получение и парсинг таблицы тестов
table = parser.get_tests_table()
tests_data = downloader.parse_tests_table(str(table))

# Загрузка доступных тестов
report = downloader.download_all_available_tests(tests_data)
```

## 📊 Функционал загрузки тестов

### Анализ таблицы тестов
- Автоматическое определение типов кнопок (TEST/Premium)
- Парсинг дат в формате DD-MM-YYYY
- Извлечение URL для загрузки

### Проверка существующих загрузок
- Формат названий файлов: `test_YYYY-MM-DD.html`
- Игнорирование файлов с другими форматами названий
- Автоматическое определение новых тестов для загрузки

### Загрузка и сохранение
- Загрузка только тестов с кнопкой TEST
- Пропуск тестов с кнопкой Premium
- Очистка HTML от изображений и лишнего контента
- Сохранение в папку `data/downloads`

## 📁 Структура папок

```
data/
├── downloads/                   # Загруженные HTML файлы
│   ├── test_2025-08-11.html   # Тест за 11 августа 2025
│   └── ...                     # Другие тесты
└── results/                    # Результаты анализа (Excel файлы)
```

## 🔧 Конфигурация

### Переменные окружения
- `PRACTICATEST_EMAIL` - Email для входа
- `PRACTICATEST_PASSWORD` - Пароль для входа
- `DOWNLOAD_DELAY_MIN/MAX` - Задержки между запросами
- `SESSION_TIMEOUT` - Таймаут сессии
- `MAX_RETRIES` - Максимальное количество повторных попыток

### Настройки загрузчика
- Путь для сохранения берётся из `config.yaml` (`files.downloads_folder`), по умолчанию `data/downloads`
- Формат названий файлов: `test_YYYY-MM-DD.html`
- Автоматическое создание папок

## 📈 Отчёты и статистика

### Отчёт о загрузке
- Общее количество тестов в таблице
- Количество тестов с кнопкой TEST
- Количество тестов с кнопкой Premium
- Уже загруженные даты
- Доступные для загрузки тесты

### Статистика загруженных тестов
- Общее количество файлов
- Самая старая и новая дата
- Диапазон дат в днях

## 🧪 Тестирование и примеры

- Юнит-тесты запускаются из корня проекта: `make test`
- Интеграционные демо-скрипты перенесены в `examples/` и не подхватываются pytest.

## 🚨 Безопасность

- Использование переменных окружения для хранения учётных данных
- Автоматическое закрытие сессий
- Таймауты для запросов
- Retry логика с ограничениями

## 📝 Примеры использования

### Базовый пример
```python
from download_tests import download_available_tests

# Загрузка всех доступных тестов
success = download_available_tests()
```

### Расширенный пример
```python
from practicatest_auth import PracticaTestAuth
from test_downloader import TestDownloader

# Создание загрузчика с кастомными настройками
downloader = TestDownloader(
    auth_session=auth.session,
    downloads_path="custom/downloads/path"
)

# Получение статистики
stats = downloader.get_test_statistics()
print(f"Загружено тестов: {stats['total_files']}")
```

## 🔄 Обновления

Система автоматически:
- Проверяет новые тесты на сайте
- Загружает только недостающие тесты
- Игнорирует уже загруженные тесты
- Обновляет статистику и отчёты

## 📞 Поддержка

При возникновении проблем:
1. Проверьте наличие файла `.env` с правильными данными
2. Убедитесь в стабильности интернет-соединения
3. Проверьте логи для диагностики ошибок
4. Убедитесь, что сайт practicatest.com доступен
