# Компоненты Spanish Analyser

Этот модуль содержит разделённые компоненты для анализа испанского текста, реализующие принцип единственной ответственности (SRP).

## Архитектура

### Основные компоненты

#### 1. TokenProcessor (`tokenizer.py`)
**Ответственность:** Токенизация текста
- Разбивка текста на токены
- Валидация токенов по критериям
- Фильтрация по минимальной длине
- Поддержка чисел (опционально)

#### 2. WordNormalizer (`normalizer.py`)
**Ответственность:** Нормализация слов
- Приведение к нижнему регистру
- Удаление испанских акцентов
- Unicode нормализация
- Кэширование результатов

#### 3. LemmaProcessor (`lemmatizer.py`)
**Ответственность:** Лемматизация слов
- Приведение слов к базовой форме
- Использование spaCy для испанского языка
- Батчевая обработка
- Кэширование лемм

#### 4. POSTagger (`pos_tagger.py`)
**Ответственность:** Определение частей речи
- POS-тегирование через spaCy
- Перевод тегов на русский язык
- Приоритеты изучения для частей речи
- Статистика по частям речи

#### 5. FrequencyAnalyzer (`frequency_analyzer.py`)
**Ответственность:** Анализ частотности
- Подсчёт частоты появления слов
- Статистика по документам
- Получение самых частых слов
- Фильтрация по диапазонам частот

#### 6. WordComparator (`word_comparator.py`)
**Ответственность:** Сравнение с известными словами
- Загрузка слов из Anki
- Проверка известности слов
- Фильтрация неизвестных слов
- Нормализация для сравнения

#### 7. ResultExporter (`exporter.py`)
**Ответственность:** Экспорт результатов
- Excel формат с листами
- CSV для Anki
- JSON с метаданными
- Текстовые отчёты

### Интерфейсы

Все компоненты реализуют абстрактные интерфейсы из `../interfaces/text_processor.py`, что обеспечивает:
- Единообразный API
- Возможность замены реализаций
- Лёгкость тестирования
- Расширяемость

## Использование

### Создание компонентов

```python
from spanish_analyser.components import (
    TokenProcessor,
    WordNormalizer,
    LemmaProcessor,
    POSTagger,
    FrequencyAnalyzer,
    WordComparator,
    ResultExporter
)

# Создание компонентов
tokenizer = TokenProcessor(min_length=3, include_numbers=False)
normalizer = WordNormalizer(use_cache=True)
lemmatizer = LemmaProcessor(model_name="es_core_news_md")
pos_tagger = POSTagger(model_name="es_core_news_md")
frequency_analyzer = FrequencyAnalyzer()
word_comparator = WordComparator(collection_path="path/to/anki")
exporter = ResultExporter(output_dir="data/results")
```

### Интеграция в WordAnalyzer

Новый `WordAnalyzer` координирует работу всех компонентов:

```python
from spanish_analyser.word_analyzer import WordAnalyzer

analyzer = WordAnalyzer(
    min_word_length=3,
    spacy_model="es_core_news_md",
    output_dir="data/results"
)

# Анализ текста
result = analyzer.analyze_text("Hola mundo español")

# Получение слов для изучения
unknown_words = analyzer.get_unknown_words_for_learning(result)

# Экспорт результатов
exported_files = analyzer.export_results(result, "analysis")
```

## Преимущества новой архитектуры

### 1. Принцип единственной ответственности
Каждый компонент отвечает только за одну задачу, что делает код:
- Легче понимать
- Проще тестировать
- Проще поддерживать

### 2. Модульность
Компоненты можно:
- Использовать независимо
- Заменять на другие реализации
- Тестировать изолированно
- Расширять новыми возможностями

### 3. Тестируемость
Каждый компонент покрыт юнит-тестами:
- `tests/test_token_processor.py`
- `tests/test_word_normalizer.py`
- `tests/test_word_analyzer_new.py`

### 4. Обратная совместимость
Новый `WordAnalyzer` сохраняет совместимость со старым API:
- `analyze_spanish_text()` - старый метод
- `get_word_frequency()` - старый метод
- `get_most_frequent_words()` - старый метод

## Миграция

### Поэтапный переход

1. **Этап 1:** Создание компонентов и интерфейсов ✅
2. **Этап 2:** Новый WordAnalyzer с компонентами ✅
3. **Этап 3:** Тестирование и отладка ✅
4. **Этап 4:** Обновление существующих модулей
5. **Этап 5:** Удаление старого кода

### Обновление существующих модулей

Для использования нового `WordAnalyzer` в существующих модулях:

```python
# Старый импорт
from spanish_analyser.word_analyzer import WordAnalyzer

# Новый импорт
from spanish_analyser.word_analyzer import WordAnalyzer

# API остаётся совместимым
analyzer = WordAnalyzer()
result = analyzer.analyze_spanish_text("text")
```

## Конфигурация

Компоненты используют настройки из `config.yaml`:

```yaml
text_analysis:
  min_word_length: 3
  spacy_model: "es_core_news_md"
  auto_download_spacy_model: true

anki:
  collection_path: "~/Library/Application Support/Anki2/User 1/collection.anki2"
  deck_pattern: "Spanish*"
```

## Разработка

### Добавление нового компонента

1. Создать класс в `components/`
2. Реализовать интерфейс из `interfaces/`
3. Добавить импорт в `components/__init__.py`
4. Написать тесты в `tests/`
5. Обновить `WordAnalyzer` при необходимости

### Тестирование

```bash
# Тесты всех компонентов
python -m pytest tests/test_*.py -v

# Тесты конкретного компонента
python -m pytest tests/test_token_processor.py -v

# Демо нового WordAnalyzer
python tools/dev_scripts/component_separation_demo.py
```

## Производительность

### Кэширование
Компоненты используют кэширование для улучшения производительности:
- `WordNormalizer` - кэш нормализованных слов
- `LemmaProcessor` - кэш лемм
- `FrequencyAnalyzer` - кэш частых слов

### Батчевая обработка
Поддерживается батчевая обработка для эффективности:
- `LemmaProcessor.lemmatize_batch()`
- `WordNormalizer.normalize_batch()`
- `POSTagger.get_pos_tags()`

## Планы развития

### Краткосрочные (1-2 недели)
- [ ] Интеграция с существующими модулями
- [ ] Обновление `DrivingTestsAnalyzer`
- [ ] Дополнительные тесты

### Среднесрочные (1-2 месяца)
- [ ] Новые компоненты для специфических задач
- [ ] Оптимизация производительности
- [ ] Расширенные форматы экспорта

### Долгосрочные (3-6 месяцев)
- [ ] Плагинная архитектура
- [ ] Веб-интерфейс
- [ ] Интеграция с другими NLP библиотеками
