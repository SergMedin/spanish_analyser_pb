# Пакет `spanish_analyser`

Пакет доменной логики проекта. Содержит обработку текста, частотный анализ, интеграцию с Anki и вспомогательные утилиты.

## Содержание пакета

- `text_processor.py` — нормализация и извлечение слов из испанского текста.
- `word_analyzer.py` — частотный анализ, лемматизация (spaCy), экспорт в Excel, учёт известных слов из Anki. Определение частей речи выполняется только через spaCy; при отсутствии модели части речи маркируются как «неизвестно».
- `anki_integration.py` — подключение к локальной коллекции Anki и извлечение текстов заметок.
- `anki_checker.py` — безопасный запуск инструментов, работающих с БД Anki (проверка и закрытие запущенного клиента).
- `config.py` — централизованная конфигурация из `config.yaml` и переменных окружения.

## Быстрый старт

```python
from spanish_analyser import SpanishTextProcessor, WordAnalyzer

text = "<p>Los colores del semáforo</p>"
processor = SpanishTextProcessor()
cleaned = processor.clean_text(text)
words = processor.extract_spanish_words(cleaned)

analyzer = WordAnalyzer()
analyzer.add_words_from_text(" ".join(words))
print(analyzer.get_top_words(10))
```

## Конфигурация

- Основные настройки — `config.yaml` в корне проекта.
- Часть опций считывается из окружения (см. `.env`).
- Важные параметры:
  - `text_analysis.min_word_length` — порог минимальной длины слова.
  - `text_analysis.spacy_model` — модель spaCy для испанского.
  - `text_analysis.auto_download_spacy_model` — авто-скачивание модели в рантайме (по умолчанию `false` для стабильных тестов/CI).
  - `files.downloads_folder`, `files.results_folder` — пути к данным и результатам (по умолчанию в `data/`).

## Интеграция с Anki

Используется `anki_integration.py` для чтения коллекции и `word_analyzer.py` для загрузки «известных слов».

Пример:
```python
from spanish_analyser import WordAnalyzer
from spanish_analyser.anki_integration import AnkiIntegration

with AnkiIntegration() as anki:
    analyzer = WordAnalyzer()
    analyzer.load_known_words_from_anki(anki)  # заполнит analyzer.known_words
```

## Безопасная работа с открытым клиентом Anki (`anki_checker.py`)

Когда клиент Anki открыт, его БД блокируется и прямое чтение может завершиться ошибкой. Для сценариев, которые работают с БД, используйте предзапусковую проверку:

Кратко:
```python
from spanish_analyser.anki_checker import check_anki_before_run

if not check_anki_before_run():
    # пользователь отказался закрывать Anki или прерывание
    raise SystemExit(1)
```

Расширенно:
```python
from spanish_analyser.anki_checker import AnkiChecker

checker = AnkiChecker()
checker.show_anki_status()
if checker.is_anki_running():
    if not checker.request_anki_close():
        raise SystemExit(1)
```

Особенности:
- Поддержка macOS/Windows/Linux (используются системные утилиты: `ps`, `tasklist`, `pgrep`, `osascript`, `taskkill`, `pkill`).
- Интерактивный сценарий запросит закрыть Anki и подождёт корректного завершения процесса.

## Экспорт результатов в Excel

`WordAnalyzer.export_to_excel(path)` создаёт один лист с колонками: `Word`, `Part of Speech`, `Frequency`, `Count`.

## Тесты

См. директорию `tests/` для юнит-тестов ключевых модулей. Тесты запускаются в venv:
```bash
make test
```
