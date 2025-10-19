"""
Модуль для работы с конфигурацией проекта

Функции:
- Загрузка config.yaml (+ профили: config.prod.yaml, config.test.yaml)
- ENV-переопределения (префикс SPANISH_ANALYSER_, вложенность через __)
- Валидация и подготовка директорий
- Настройка логирования
"""

import os
import yaml
import glob
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Config:
    """Класс для работы с конфигурацией проекта"""
    
    def __init__(self, config_path: str = None):
        """
        Инициализация конфигурации
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Ищем config.yaml в корне проекта
            current_dir = Path.cwd()
            config_path = current_dir / "config.yaml"
            
            # Если не найден в текущей директории, ищем в родительских
            while not config_path.exists() and current_dir.parent != current_dir:
                current_dir = current_dir.parent
                config_path = current_dir / "config.yaml"
            
            self.config_path = config_path
        
        self.config_data = {}
        self.env_data = {}
        
        # Загружаем конфигурацию
        self._load_config()
        self._load_env()
        # Применяем ENV-переопределения и профили
        try:
            self._apply_env_overrides()
            self._validate_and_prepare()
        except Exception as e:
            logger.warning(f"Проблема при применении ENV/валидации: {e}")
        # Настраиваем логирование согласно конфигу (идемпотентно, с возможностью переинициализации)
        self._configure_logging_if_needed()
    
    def _load_config(self):
        """Загружает конфигурацию из YAML файла"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config_data = yaml.safe_load(f) or {}
                logger.info(f"Конфигурация загружена: {self.config_path}")
            else:
                logger.warning(f"Файл конфигурации {self.config_path} не найден, используются значения по умолчанию")
                self.config_data = self._get_default_config()
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            self.config_data = self._get_default_config()
    
    def _load_env(self):
        """Загружает переменные окружения из .env файла"""
        try:
            load_dotenv()
            self.env_data = {
                'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
                'PRACTICATEST_EMAIL': os.getenv('PRACTICATEST_EMAIL'),
                'PRACTICATEST_PASSWORD': os.getenv('PRACTICATEST_PASSWORD'),
            }
            logger.info("Переменные окружения загружены из .env (если есть)")
        except Exception as e:
            logger.error(f"Ошибка загрузки переменных окружения: {e}")
    
    # --- Профили/ENV overrides/валидация/логирование ---
    def _resolve_config_path(self) -> Path:
        env = os.getenv('SPANISH_ANALYSER_ENV', '').lower().strip()
        root = self.config_path.parent if self.config_path else Path.cwd()
        candidate: Path
        if env == 'production':
            candidate = root / 'config.prod.yaml'
        elif env == 'testing':
            candidate = root / 'config.test.yaml'
        else:
            candidate = root / 'config.yaml'
        if candidate.exists():
            return candidate
        # Фолбэк на исходный путь
        return self.config_path

    def _load_config(self):
        """Загружает конфигурацию из YAML файла"""
        try:
            # Выбор файла с учётом профиля окружения
            self.config_path = self._resolve_config_path()
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config_data = yaml.safe_load(f) or {}
                logger.info(f"Конфигурация загружена: {self.config_path}")
            else:
                logger.warning(f"Файл конфигурации {self.config_path} не найден, используются значения по умолчанию")
                self.config_data = self._get_default_config()
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            self.config_data = self._get_default_config()

    def _set_nested(self, data: Dict[str, Any], dotted: str, value: Any) -> None:
        cur = data
        keys = dotted.split('.')
        for k in keys[:-1]:
            if k not in cur or not isinstance(cur[k], dict):
                cur[k] = {}
            cur = cur[k]
        cur[keys[-1]] = value

    def _apply_env_overrides(self) -> None:
        """Переопределяет конфиг значениями из ENV (SPANISH_ANALYSER_*)."""
        prefix = 'SPANISH_ANALYSER_'
        for key, val in os.environ.items():
            if not key.startswith(prefix):
                continue
            # Пропускаем служебные (ENV/DEBUG и т.п.)
            if key in ('SPANISH_ANALYSER_ENV',):
                continue
            tail = key[len(prefix):]
            # Вложенность разделяется двойным подчёркиванием
            dotted = tail.replace('__', '.').lower()
            # Пытаемся привести числа/булевы
            parsed: Any = val
            if val.lower() in ('true', 'false'):
                parsed = (val.lower() == 'true')
            else:
                try:
                    if '.' in val:
                        parsed = float(val)
                    else:
                        parsed = int(val)
                except ValueError:
                    parsed = val
            self._set_nested(self.config_data, dotted, parsed)
        if os.getenv('SPANISH_ANALYSER_ENV'):
            logger.info(f"Активирован профиль: {os.getenv('SPANISH_ANALYSER_ENV')}")

    def _validate_and_prepare(self) -> None:
        """Проверяет диапазоны и создаёт нужные директории."""
        try:
            min_len = int(self.get('text_analysis.min_word_length', 3))
            if min_len < 1:
                logger.warning("min_word_length < 1 — принудительно установлено в 1")
                self._set_nested(self.config_data, 'text_analysis.min_word_length', 1)
        except Exception:
            self._set_nested(self.config_data, 'text_analysis.min_word_length', 3)
        # Директории
        try:
            Path(self.get_downloads_folder()).mkdir(parents=True, exist_ok=True)
            Path(self.get_results_folder()).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.debug(f"Не удалось создать директории результатов/загрузок: {e}")

    def _configure_logging_if_needed(self, force: bool = False) -> None:
        """Инициализирует/переинициализирует базовое логирование по config.

        Повторная конфигурация выполняется, если:
          - ранее не конфигурировалось, или
          - изменился уровень/формат/файл логирования, или
          - явно указан force=True
        """
        root = logging.getLogger()

        # Получаем раздельные уровни для консоли и файла
        console_level_name = str(self.get_console_logging_level()).upper()
        file_level_name = str(self.get_file_logging_level()).upper()
        console_level = getattr(logging, console_level_name, logging.INFO)
        file_level = getattr(logging, file_level_name, logging.DEBUG)
        
        desired_fmt = self.get_logging_format()
        desired_file = self.get_logging_file() if self.is_logging_to_file_enabled() else None

        if getattr(root, "_spanish_analyser_configured", False) and not force:
            # Проверим, не изменились ли параметры
            current_console_level = getattr(root, "_spanish_analyser_console_level", None)
            current_file_level = getattr(root, "_spanish_analyser_file_level", None)
            current_fmt = getattr(root, "_spanish_analyser_format", None)
            current_file = getattr(root, "_spanish_analyser_file", None)
            if (
                current_console_level == console_level_name and
                current_file_level == file_level_name and
                current_fmt == desired_fmt and
                current_file == desired_file
            ):
                return

        handlers: List[logging.Handler] = []
        # Консоль с уровнем для пользователя (INFO)
        console = logging.StreamHandler()
        console.setLevel(console_level)
        console.setFormatter(logging.Formatter(desired_fmt))
        handlers.append(console)
        
        # Файл при необходимости с уровнем для техники (DEBUG)
        if desired_file:
            # Очищаем старые логи перед созданием нового
            self.cleanup_old_log_files()
            
            log_file = Path(desired_file)
            try:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                fh = logging.FileHandler(log_file, encoding='utf-8')
                fh.setLevel(file_level)
                fh.setFormatter(logging.Formatter(desired_fmt))
                handlers.append(fh)
            except Exception as e:
                logger.debug(f"Не удалось открыть файл лога: {e}")

        # Устанавливаем минимальный уровень для root logger (DEBUG для файла)
        root_level = min(console_level, file_level) if desired_file else console_level
        logging.basicConfig(level=root_level, handlers=handlers, format=desired_fmt, force=True)
        setattr(root, "_spanish_analyser_configured", True)
        setattr(root, "_spanish_analyser_console_level", console_level_name)
        setattr(root, "_spanish_analyser_file_level", file_level_name)
        setattr(root, "_spanish_analyser_format", desired_fmt)
        setattr(root, "_spanish_analyser_file", desired_file)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию"""
        return {
            'anki': {
                'collection_path': "~/Library/Application Support/Anki2/User 1/collection.anki2",
                'deck_pattern': "Spanish*",
                'field_names': ["FrontText", "BackText"],
                # Включаем lemma-aware проверку известности по умолчанию
                'lemma_aware_known': True
            },
            'text_analysis': {
                'min_word_length': 3,
                'max_words_export': 1000,
                'enable_pos_tagging': True,
                'spacy_model': "es_core_news_md",
                # Безопасный флаг: не пытаться скачивать модель автоматически в рантайме
                # Это важно для окружений CI/офлайн и для быстрых юнит-тестов
                'auto_download_spacy_model': False,
                # Настройки современных моделей (SPEC-04)
                'primary_model': {
                    'type': 'spacy',
                    'name': 'es_core_news_md'
                },
                # Политика No Fallback: резервная модель запрещена
                'available_models': [
                    {'type': 'spacy', 'name': 'es_core_news_sm', 'install': 'python -m spacy download es_core_news_sm'},
                    {'type': 'spacy', 'name': 'es_core_news_md', 'install': 'python -m spacy download es_core_news_md'}
                ]
            },
            'web_scraper': {
                'base_url': "https://practicatest.com",
                'timeout': 30,
                'user_agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
            'files': {
                'downloads_folder': "data/downloads",
                'results_folder': "data/results",
                'max_results_files': 20,
                'results_filename_prefix': "driving_tests_analysis"
            },
            'excel': {
                'frequency_decimal_places': 2,
                'include_headers': True,
                'main_sheet_name': "Word Analysis"
            },
            'logging': {
                'level': "INFO",
                'format': "%(asctime)s - %(levelname)s - %(message)s",
                'log_to_file': False,
                'log_file': "logs/spanish_analyser.log"
            },
            # Новый раздел кэширования (заменяет performance.*)
            'cache': {
                # Корневая папка кэша. Подпулы кэша используют подпапки внутри неё.
                'root_dir': 'cache',
                # Лимит размера для каждого подпула кэша (в МБ)
                'max_size_mb': 256,
                # Кэш извлечённых текстов из HTML/документов
                'html': {
                    'enabled': True,   # включает/выключает кэширование извлечения текста
                    'dir': 'texts',    # подпапка в root_dir
                    'ttl_days': 7      # срок жизни записей (дней)
                },
                # Кэш данных Anki (списки слов и др.)
                'anki': {
                    'enabled': True,
                    'dir': 'anki',
                    'ttl_days': 3
                },
                # Кэш результатов spaCy (леммы, POS)
                'spacy': {
                    'enabled': True,
                    'dir': 'spacy',
                    'ttl_days': 30
                },
                # Кэш результатов OpenAI API
                'openai': {
                    'enabled': True,
                    'dir': 'openai',
                    'ttl_days': 7
                },
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получает значение конфигурации по ключу
        
        Args:
            key: Ключ в формате 'section.subsection.parameter'
            default: Значение по умолчанию
            
        Returns:
            Значение параметра или default
        """
        try:
            keys = key.split('.')
            value = self.config_data
            
            for k in keys:
                value = value[k]
            
            return value
        except (KeyError, TypeError):
            return default
    
    def get_env(self, key: str, default: Any = None) -> Any:
        """
        Получает значение переменной окружения
        
        Args:
            key: Ключ переменной окружения
            default: Значение по умолчанию
            
        Returns:
            Значение переменной окружения или default
        """
        return self.env_data.get(key, default)
    
    def get_anki_config(self) -> Dict[str, Any]:
        """Получает конфигурацию Anki"""
        return self.config_data.get('anki', {})
    
    def get_text_analysis_config(self) -> Dict[str, Any]:
        """Получает конфигурацию анализа текста"""
        return self.config_data.get('text_analysis', {})

    # --- Modern models (SPEC-04) ---
    def get_primary_model_config(self) -> Dict[str, Any]:
        """Настройки основной языковой модели (тип/имя)."""
        return self.get('text_analysis.primary_model', {}) or {}

    # Резервная модель удалена политикой No Fallback

    def get_available_models(self) -> Any:
        """Список доступных моделей с подсказками по установке."""
        return self.get('text_analysis.available_models', [])
    
    def get_web_scraper_config(self) -> Dict[str, Any]:
        """Получает конфигурацию веб-скрапера"""
        return self.config_data.get('web_scraper', {})
    
    def get_files_config(self) -> Dict[str, Any]:
        """Получает конфигурацию файлов"""
        return self.config_data.get('files', {})
    
    def get_excel_config(self) -> Dict[str, Any]:
        """Получает конфигурацию Excel"""
        return self.config_data.get('excel', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Получает конфигурацию логирования"""
        return self.config_data.get('logging', {})
    
    def get_collection_path(self) -> str:
        """Получает путь к коллекции Anki"""
        path = self.get('anki.collection_path')
        return os.path.expanduser(path)
    
    def get_deck_pattern(self) -> str:
        """Получает паттерн для поиска колод"""
        return self.get('anki.deck_pattern', "Spanish*")
    
    def get_field_names(self) -> List[str]:
        """Получает названия полей для извлечения слов"""
        return self.get('anki.field_names', ["FrontText", "BackText"])
    
    def get_downloads_folder(self) -> str:
        """Получает папку для загрузок"""
        return self.get('files.downloads_folder', "data/downloads")
    
    def get_results_folder(self) -> str:
        """Получает папку для результатов"""
        return self.get('files.results_folder', "data/results")
    
    def get_max_results_files(self) -> int:
        """Получает максимальное количество файлов результатов"""
        return self.get('files.max_results_files', 20)
    
    def get_results_filename_prefix(self) -> str:
        """Получает префикс для файлов результатов"""
        return self.get('files.results_filename_prefix', "driving_tests_analysis")
    
    def get_frequency_decimal_places(self) -> int:
        """Получает количество знаков после запятой для частоты"""
        return self.get('excel.frequency_decimal_places', 2)
    
    def get_main_sheet_name(self) -> str:
        """Получает название основного листа Excel"""
        return self.get('excel.main_sheet_name', "Word Analysis")
    
    def get_spacy_model(self) -> str:
        """Получает название модели spaCy"""
        return self.get('text_analysis.spacy_model', "es_core_news_md")
    
    def get_min_word_length(self) -> int:
        """Получает минимальную длину слова"""
        return self.get('text_analysis.min_word_length', 3)

    def is_auto_download_spacy_model_enabled(self) -> bool:
        """Возвращает, разрешено ли автоскачивание модели spaCy"""
        return self.get('text_analysis.auto_download_spacy_model', False)
    
    def get_web_scraper_timeout(self) -> int:
        """Получает таймаут для веб-скрапера"""
        return self.get('web_scraper.timeout', 30)
    
    def get_web_scraper_base_url(self) -> str:
        """Получает базовый URL для веб-скрапера"""
        return self.get('web_scraper.base_url', "https://practicatest.com")
    
    def get_web_scraper_user_agent(self) -> str:
        """Получает User-Agent для веб-скрапера"""
        return self.get('web_scraper.user_agent', "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    
    def get_min_spanish_ratio(self) -> float:
        """Получает минимальную долю испанского текста для Anki"""
        return self.get('anki.min_spanish_ratio', 0.3)
    
    def is_lemma_aware_known_enabled(self) -> bool:
        """Включить ли режим известности по лемме для глаголов/частей речи."""
        return bool(self.get('anki.lemma_aware_known', False))
    
    def get_console_logging_level(self) -> str:
        """Получает уровень логирования для консоли"""
        # Поддержка старого формата logging.level для обратной совместимости
        return self.get('logging.console_level', self.get('logging.level', "INFO"))
    
    def get_file_logging_level(self) -> str:
        """Получает уровень логирования для файла"""
        return self.get('logging.file_level', "DEBUG")
    
    def get_logging_level(self) -> str:
        """Получает уровень логирования (для обратной совместимости)"""
        return self.get_console_logging_level()
    
    def get_logging_format(self) -> str:
        """Получает формат логов"""
        return self.get('logging.format', "%(asctime)s - %(levelname)s - %(message)s")
    
    def get_logging_file(self) -> str:
        """Получает путь к файлу логов"""
        # Если включено логирование в файл, используем файл с временной меткой
        if self.is_logging_to_file_enabled():
            return self.get_session_log_file()
        
        # Для статичного лога заменяем {timestamp} на реальную временную метку
        log_file_template = self.get('logging.log_file', "logs/spanish_analyser.log")
        if "{timestamp}" in log_file_template:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return log_file_template.replace("{timestamp}", timestamp)
        return log_file_template
    
    def is_logging_to_file_enabled(self) -> bool:
        """Проверяет, включено ли логирование в файл"""
        return self.get('logging.log_to_file', False)
    
    def get_session_log_file(self) -> str:
        """Генерирует имя файла лога для текущей сессии с временной меткой"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"logs/spanish_analyser_{timestamp}.log"
    
    def get_max_log_files(self) -> int:
        """Получает максимальное количество файлов логов для хранения"""
        return self.get('logging.max_log_files', 10)
    
    def cleanup_old_log_files(self) -> None:
        """Удаляет старые файлы логов, оставляя только последние max_log_files"""
        try:
            logs_dir = Path("logs")
            if not logs_dir.exists():
                return
            
            # Находим все файлы логов
            log_pattern = "spanish_analyser_*.log"
            log_files = list(logs_dir.glob(log_pattern))
            
            max_files = self.get_max_log_files()
            
            if len(log_files) <= max_files:
                return
            
            # Сортируем по времени модификации (самые новые последними)
            log_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Удаляем старые файлы
            files_to_remove = log_files[:-max_files]
            for old_file in files_to_remove:
                try:
                    old_file.unlink()
                    logger.debug(f"Удален старый лог файл: {old_file}")
                except Exception as e:
                    logger.debug(f"Не удалось удалить лог файл {old_file}: {e}")
                    
        except Exception as e:
            logger.debug(f"Ошибка при очистке старых логов: {e}")
    
    def is_pos_tagging_enabled(self) -> bool:
        """Проверяет, включено ли определение частей речи"""
        return self.get('text_analysis.enable_pos_tagging', True)

    def use_context_pipeline(self) -> bool:
        """Возвращает, использовать ли контекстный пайплайн обработки текста."""
        return bool(self.get('text_analysis.use_context_pipeline', False))

    # --- Caching (new layout) ---
    def _days_to_seconds(self, days: int | float) -> int:
        try:
            return int(float(days) * 86400)
        except Exception:
            return int(7 * 86400)

    # Root and limits
    def get_cache_root_dir(self) -> str:
        return self.get('cache.root_dir', self.get('performance.cache_dir', 'cache'))

    def get_cache_max_size_mb(self) -> int:
        return int(self.get('cache.max_size_mb', self.get('performance.max_size_mb', 256)))

    # HTML cache
    def is_html_cache_enabled(self) -> bool:
        return bool(self.get('cache.html.enabled', self.get('performance.cache_html_extraction', True)))

    def get_cache_html_dir(self) -> str:
        root = self.get_cache_root_dir()
        sub = self.get('cache.html.dir', 'texts')
        return str(Path(root) / sub)

    def get_cache_html_ttl_seconds(self) -> int:
        days = self.get('cache.html.ttl_days', None)
        if days is None:
            # fallback to old performance.ttl_seconds
            return int(self.get('performance.ttl_seconds', 86400))
        return self._days_to_seconds(days)

    # Anki cache
    def is_anki_cache_enabled(self) -> bool:
        return bool(self.get('cache.anki.enabled', self.get('performance.cache_anki_words', True)))

    def get_cache_anki_dir(self) -> str:
        root = self.get_cache_root_dir()
        sub = self.get('cache.anki.dir', 'anki')
        return str(Path(root) / sub)

    def get_cache_anki_ttl_seconds(self) -> int:
        days = self.get('cache.anki.ttl_days', None)
        if days is None:
            return int(self.get('performance.ttl_seconds', 86400))
        return self._days_to_seconds(days)

    # spaCy cache
    def is_spacy_cache_enabled(self) -> bool:
        return bool(self.get('cache.spacy.enabled', self.get('performance.cache_spacy_results', True)))

    def get_cache_spacy_dir(self) -> str:
        root = self.get_cache_root_dir()
        sub = self.get('cache.spacy.dir', 'spacy')
        return str(Path(root) / sub)

    def get_cache_spacy_ttl_seconds(self) -> int:
        days = self.get('cache.spacy.ttl_days', None)
        if days is None:
            return int(self.get('performance.ttl_seconds', 86400))
        return self._days_to_seconds(days)

    # Backwards compatible helpers used around the codebase
    def should_cache_html_extraction(self) -> bool:
        return self.is_html_cache_enabled()

    def should_cache_anki_words(self) -> bool:
        return self.is_anki_cache_enabled()

    def should_cache_spacy_results(self) -> bool:
        return self.is_spacy_cache_enabled()

    # openai cache
    def is_openai_cache_enabled(self) -> bool:
        return bool(self.get('cache.openai.enabled', True))

    def get_cache_openai_dir(self) -> str:
        root = self.get_cache_root_dir()
        sub = self.get('cache.openai.dir', 'openai')
        return str(Path(root) / sub)

    def get_cache_openai_ttl_seconds(self) -> int:
        days = self.get('cache.openai.ttl_days', 7)
        return self._days_to_seconds(days)

    def should_cache_openai_results(self) -> bool:
        return self.is_openai_cache_enabled()

    # --- AI / OpenAI ---
    def get_ai_model(self) -> str:
        """Получает модель OpenAI для генерации перевода."""
        return self.get('ai.model', 'gpt-5')

    def get_ai_workers(self) -> int:
        """Текущее количество потоков для параллельной генерации переводов."""
        try:
            workers = int(self.get('ai.concurrency.workers', 3))
        except Exception:
            workers = 3
        return max(1, workers)

    def get_ai_base_delay(self) -> float:
        """Базовая задержка между запросами к OpenAI (секунды)."""
        return float(self.get('ai.rate_limiting.base_delay', 0.5))

    def get_ai_max_retry_delay(self) -> float:
        """Максимальная задержка при rate limiting (секунды)."""
        return float(self.get('ai.rate_limiting.max_retry_delay', 15))

    def get_ai_max_retries(self) -> int:
        """Количество попыток при ошибках."""
        return int(self.get('ai.rate_limiting.max_retries', 3))

    # --- Music (Chiptune) ---
    def is_chiptune_enabled(self) -> bool:
        return self.get('music.chiptune_enabled', False)

    def get_chiptune_preset(self) -> str:
        return self.get('music.chiptune_preset', 'cambio_groove')

    def get_chiptune_tempo(self) -> float:
        return float(self.get('music.chiptune_tempo', 0.11))

    def get_chiptune_duration(self) -> int:
        return int(self.get('music.chiptune_duration', 150))

    def get_chiptune_amp(self) -> float:
        return float(self.get('music.chiptune_amp', 0.15))

    def get_audio_device(self):
        return self.get('music.audio_device', None)


# Глобальный экземпляр конфигурации
config = Config()
