# Лучшие практики использования spaCy в проекте

## Проблема с омонимами и контекстом

### Что было не так
До внедрения лучших практик в проекте была проблема с обработкой омонимов:
- Токенизатор извлекал отдельные слова без контекста
- POS-теггер получал `["además", "capital", "españa", ...]` вместо полного текста
- spaCy видел "capital" без артикля "la"/"el" и определял его неправильно

### Пример проблемы
```python
# НЕПРАВИЛЬНО (старый подход)
tokens = ["además", "capital", "españa", "madrid", "capital", "puede"]
pos_tags = pos_tagger.get_pos_tags(tokens)  # Теряется контекст!
# Результат: capital определяется как PROPN (собственное имя)
```

## Решение: унифицированный пайплайн

### Лучшие практики spaCy
1. **Обрабатывать полный текст с контекстом** - не отдельные слова
2. **Сохранять связь между токенами и оригинальным текстом**
3. **Использовать современные трансформерные модели** (`es_dep_news_trf`)
4. **Извлекать морфологическую информацию** в одном проходе
5. **Применять фильтры проекта после анализа spaCy**

### Новая архитектура
```python
# ПРАВИЛЬНО (новый подход)
from spanish_analyser.components.text_pipeline import SpanishTextPipeline

pipeline = SpanishTextPipeline()
context = pipeline.analyze_text(full_text)  # Полный контекст!

# Результат: правильное определение омонимов
# "la capital" -> NOUN, Gender=Fem -> "la capital"
# "el capital" -> NOUN, Gender=Masc -> "el capital"
```

## Компонент SpanishTextPipeline

### Основные возможности
- ✅ Обработка полного текста с контекстом
- ✅ Сохранение морфологической информации
- ✅ Правильное сопоставление токенов
- ✅ Фильтрация по правилам проекта
- ✅ Извлечение контекста вокруг токенов
- ✅ Форматирование существительных с артиклями

### Использование

#### Базовый анализ
```python
pipeline = SpanishTextPipeline()
context = pipeline.analyze_text("La capital de España es Madrid")

# Получить валидные токены
valid_tokens = pipeline.get_filtered_tokens(context)

# Получить только существительные
nouns = pipeline.get_tokens_by_pos(context, ['NOUN'])
```

#### Работа с родом существительных
```python
# Получить существительные с информацией о роде
nouns_with_gender = pipeline.get_nouns_with_gender(context)

for token, gender in nouns_with_gender:
    formatted = pipeline.format_noun_with_article(token.lemma, gender)
    print(f"{token.text} -> {formatted}")
    # capital -> la capital (если gender=Fem)
    # capital -> el capital (если gender=Masc)
```

#### Извлечение контекста
```python
for token in valid_tokens:
    if 'capital' in token.text:
        ctx = pipeline.get_context_around_token(context, token, window=3)
        print(f"Контекст: ...{ctx}...")
```

## Результаты применения

### До (проблемы)
- ❌ "capital" определялся как PROPN или ADJ без контекста
- ❌ Омонимы не различались по роду/смыслу
- ❌ Потеря морфологической информации

### После (решение)
- ✅ "la capital" → NOUN, Fem → ключ частотности "la capital"
- ✅ "el capital" → NOUN, Masc → ключ частотности "el capital"
- ✅ Сохранение полной морфологической информации
- ✅ Правильный контекст для всех токенов

## Интеграция в проект

### Обновлённые компоненты
1. **SpanishTextPipeline** - новый унифицированный пайплайн
2. **word_analyzer_simple_demo.py** - обновлённый демо-скрипт
3. **WordAnalyzer** - будет обновлён для использования пайплайна
4. **Экспортёры** - будут использовать контекстную информацию

### Совместимость
- Новый пайплайн совместим с существующими компонентами
- Старые компоненты сохранены для обратной совместимости
- Постепенная миграция на новую архитектуру

## Настройки модели

### Рекомендуемая модель
```yaml
# config.yaml
text_analysis:
  spacy_model: "es_dep_news_trf"  # Трансформерная модель
  primary_model:
    type: spacy
    name: es_dep_news_trf
```

### Установка зависимостей
```bash
pip install -U "spacy[transformers]"
python -m spacy download es_dep_news_trf
```

## Тестирование

### Проверка работы пайплайна
```python
# Тест на омонимах
text = "La capital de España es Madrid, pero el capital puede referirse al dinero."
context = pipeline.analyze_text(text)

capital_tokens = [t for t in pipeline.get_filtered_tokens(context) if 'capital' in t.text]
assert len(capital_tokens) == 2
assert capital_tokens[0].morph.get('Gender') == ['Fem']  # la capital
assert capital_tokens[1].morph.get('Gender') == ['Masc'] # el capital
```

### Запуск демо
```bash
source venv/bin/activate
python tools/dev_scripts/word_analyzer_simple_demo.py
```

В демо-скрипте теперь есть специальный "Шаг 5", который показывает решение проблемы с "capital".

## Заключение

Внедрение лучших практик spaCy решило проблему с омонимами и обеспечило:
- Корректное определение частей речи в контексте
- Различение омонимов по роду и смыслу
- Сохранение полной морфологической информации
- Правильное форматирование ключей частотности

Новый `SpanishTextPipeline` является основой для дальнейшего развития проекта.
