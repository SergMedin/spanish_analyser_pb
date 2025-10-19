# Makefile для Spanish Analyser

.PHONY: help install test test-q test-coverage clean demo lint format cli venv-activate investigate scrape analyze anki-deck full demo-auth demo-parser demo-real-auth cli-debug fix-venv

# Переменные
# Явно используем zsh как shell, чтобы корректно открывать интерактивную сессию
SHELL := /bin/zsh
PYTHON = python3
PIP = pip3
VENV = venv
SRC_DIR = src
TESTS_DIR = tests

# Цвета для вывода
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

help: ## Показать справку по командам
	@echo "$(GREEN)Доступные команды:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Установить зависимости
	@echo "$(GREEN)Создание виртуального окружения...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)Активация виртуального окружения...$(NC)"
	. $(VENV)/bin/activate && $(PIP) install --upgrade pip
	@echo "$(GREEN)Установка зависимостей...$(NC)"
	. $(VENV)/bin/activate && $(PIP) install -r requirements.txt
	@echo "$(GREEN)Установка модуля в режиме разработки...$(NC)"
	. $(VENV)/bin/activate && $(PIP) install -e .

install-dev: ## Установить зависимости для разработки
	@echo "$(GREEN)Установка зависимостей для разработки...$(NC)"
	. $(VENV)/bin/activate && $(PIP) install -e ".[dev]"

test: ## Запустить тесты
	@echo "$(GREEN)Запуск тестов...$(NC)"
	. $(VENV)/bin/activate && $(PYTHON) -m pytest $(TESTS_DIR)/ -v

test-q: ## Запустить тесты в тихом режиме (без obsoleted shebang), эквивалент 'python -m pytest -q'
	@echo "$(GREEN)Запуск тестов (quiet)...$(NC)"
	. $(VENV)/bin/activate && $(PYTHON) -m pytest -q

test-coverage: ## Запустить тесты с покрытием
	@echo "$(GREEN)Запуск тестов с покрытием...$(NC)"
	. $(VENV)/bin/activate && $(PYTHON) -m pytest $(TESTS_DIR)/ --cov=$(SRC_DIR)/spanish_analyser --cov-report=html

demo: ## Запустить демонстрацию основных возможностей
	@echo "$(GREEN)Запуск демонстрации...$(NC)"
	PYTHONPATH=$(SRC_DIR):$$PYTHONPATH $(VENV)/bin/python $(SRC_DIR)/main.py

cli: ## Запустить интерактивную консоль утилит
	@echo "$(GREEN)Запуск интерактивного CLI...$(NC)"
	PYTHONPATH=$(SRC_DIR):$$PYTHONPATH $(VENV)/bin/python -m spanish_analyser.cli

cli-debug: ## Запустить CLI в режиме отладки
	@echo "$(YELLOW)Запуск CLI в режиме отладки...$(NC)"
	SPANISH_ANALYSER_DEBUG=1 PYTHONPATH=$(SRC_DIR):$$PYTHONPATH $(VENV)/bin/python -m spanish_analyser.cli

lint: ## Проверить код линтером
	@echo "$(GREEN)Проверка кода...$(NC)"
	. $(VENV)/bin/activate && flake8 $(SRC_DIR)/ $(TESTS_DIR)/

format: ## Форматировать код
	@echo "$(GREEN)Форматирование кода...$(NC)"
	. $(VENV)/bin/activate && black $(SRC_DIR)/ $(TESTS_DIR)/

clean: ## Очистить временные файлы
	@echo "$(GREEN)Очистка временных файлов...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -f .coverage

venv-activate: ## Активировать виртуальное окружение
	@echo "$(GREEN)Для активации виртуального окружения выполните:$(NC)"
	@echo "$(YELLOW)source $(VENV)/bin/activate$(NC)"

check-venv: ## Проверить виртуальное окружение
	@if [ -d "$(VENV)" ]; then \
		echo "$(GREEN)Виртуальное окружение найдено в $(VENV)$(NC)"; \
	else \
		echo "$(RED)Виртуальное окружение не найдено. Выполните 'make install'$(NC)"; \
	fi

venv-shell: ## Открыть интерактивную оболочку с активированным venv
	@if [ -d "$(VENV)" ]; then \
		echo "$(GREEN)Открываю интерактивную оболочку с активированным окружением $(VENV)...$(NC)"; \
		. $(VENV)/bin/activate && exec $(SHELL) -i; \
	else \
		echo "$(RED)Виртуальное окружение не найдено. Сначала выполните 'make install'.$(NC)"; \
		exit 1; \
	fi

fix-venv: ## Переcоздать виртуальное окружение и установить зависимости (устраняет bad interpreter)
	@echo "$(YELLOW)Удаляю старый venv...$(NC)"
	rm -rf $(VENV)
	@echo "$(GREEN)Создаю новое окружение...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)Устанавливаю зависимости...$(NC)"
	. $(VENV)/bin/activate && $(PIP) install --upgrade pip && $(PIP) install -r requirements.txt && $(PIP) install -e .
	@echo "$(GREEN)Готово. Запускаю тесты...$(NC)"
	. $(VENV)/bin/activate && $(PYTHON) -m pytest -q

scrape: ## Запустить веб-скрапер (загрузка тестов practicatest.com)
	@echo "$(GREEN)Запуск веб-скрапера...$(NC)"
	SPANISH_ANALYSER_LOGGING__LOG_TO_FILE=true \
	PYTHONPATH=$(SRC_DIR):$$PYTHONPATH $(VENV)/bin/python -m spanish_analyser.cli --scraper

analyze: ## Запустить анализатор загруженных HTML и экспорт в Excel
	@echo "$(GREEN)Запуск анализатора билетов...$(NC)"
	SPANISH_ANALYSER_LOGGING__LOG_TO_FILE=true \
	PYTHONPATH=$(SRC_DIR):$$PYTHONPATH $(VENV)/bin/python -m spanish_analyser.cli --analyzer

anki-deck: ## Запустить генератор Anki колод
	@echo "$(GREEN)Запуск генератора Anki колод...$(NC)"
	SPANISH_ANALYSER_LOGGING__LOG_TO_FILE=true \
	PYTHONPATH=$(SRC_DIR):$$PYTHONPATH $(VENV)/bin/python -m spanish_analyser.cli --anki-generator

full: ## Полный цикл: скрапинг + анализ + генерация колод
	@echo "$(GREEN)Полный цикл: скрапинг -> анализ -> генерация колод...$(NC)"
	SPANISH_ANALYSER_LOGGING__LOG_TO_FILE=true \
	PYTHONPATH=$(SRC_DIR):$$PYTHONPATH $(VENV)/bin/python -m spanish_analyser.cli --all

investigate: ## Исследовать слово в текстах и Anki (WORD=palabra)
	@if [ -z "$(WORD)" ]; then \
		echo "$(RED)Укажите слово: make investigate WORD=palabra$(NC)"; exit 1; \
	fi
	PYTHONPATH=$(SRC_DIR):$$PYTHONPATH $(VENV)/bin/python $(SRC_DIR)/spanish_analyser/tools/text_analyzer/word_investigator.py $(WORD)

demo-auth: ## Демо: авторизация practicatest.com
	. $(VENV)/bin/activate && $(PYTHON) $(SRC_DIR)/spanish_analyser/tools/web_scraper/examples/auth_demo.py

demo-parser: ## Демо: парсер practicatest.com
	. $(VENV)/bin/activate && $(PYTHON) $(SRC_DIR)/spanish_analyser/tools/web_scraper/examples/parser_demo.py

demo-real-auth: ## Демо: реальная авторизация + доступ к странице
	. $(VENV)/bin/activate && $(PYTHON) $(SRC_DIR)/spanish_analyser/tools/web_scraper/examples/real_auth_demo.py
