#!/usr/bin/env python3
"""
Интерактивный пошаговый демо-скрипт: как работает анализатор испанского текста с ANKI.

Что делает скрипт:
- Загружает конфигурацию проекта (`config.yaml`)
- Показывает тестовый текст на испанском
- Пошагово выполняет: токенизацию → POS-теги → лемматизацию → частоты → сбор результата
- НОВОЕ: Подробно демонстрирует интеграцию с ANKI:
  * Подключение к AnkiConnect
  * Извлечение Notes (заметок) из испанских колод
  * Логику определения известности слов
  * Поиск похожих терминов для неизвестных слов
- На каждом шаге выводит понятные пояснения и таблицы
- Ждёт нажатия пробела, чтобы продолжить к следующему шагу

Как запускать:
1) Активировать venv: `source venv/bin/activate`
2) Убедиться, что ANKI запущен с плагином AnkiConnect (код: 2055492159)
3) Запустить: `python tools/dev_scripts/word_analyzer_simple_demo.py`

Примечание: скрипт использует проектные компоненты из `src/spanish_analyser/...`.
Если ANKI недоступен, скрипт покажет демо-режим с тестовыми данными.
"""

import os
import sys
import time
from typing import List

# Добавляем путь к src (сохраняем относительный запуск из корня проекта)
sys.path.append('src')

from spanish_analyser.config import config
from spanish_analyser.components.tokenizer import TokenProcessor
from spanish_analyser.components.pos_tagger import POSTagger
from spanish_analyser.components.lemmatizer import LemmaProcessor
from spanish_analyser.components.frequency_analyzer import FrequencyAnalyzer
from spanish_analyser.components.text_pipeline import SpanishTextPipeline
from spanish_analyser.components.word_comparator import WordComparator
from spanish_analyser.interfaces.text_processor import WordInfo, AnalysisResult
from spanish_analyser.word_analyzer import WordAnalyzer


TEST_TEXT = (
    "La casa es muy grande y hermosa. Yo corro rápido en el parque todos los días. "
    "Este libro es muy interesante para estudiar. El niño come frutas frescas. "
    "Además, la capital de España es Madrid, una ciudad moderna. Barcelona también es importante. "
    "El capital inicial fue insuficiente para el proyecto. María trabajó en París. "
    "Las capitales europeas son fascinantes, pero los capitales extranjeros dominan el mercado. "
    "El herido está estable en el hospital, mientras que la herida necesita limpieza urgente. "
    "Las heridas cicatrizan lentamente, pero los heridos se recuperan bien. "
    "Ella es muy bonita y elegante, él es bonito y simpático. "
    "También vemos formas como bonita, bonito, bonitas y bonitos en descripciones literarias. "
    "La mesa está limpia. El agua está fría. Los libros están ordenados. "
    "Las personas trabajadoras merecen respeto. Los trabajadores industriales son importantes. "
    "La economía mundial depende de múltiples factores complejos y variables. Google es una empresa americana."
)


def pause(step_title: str) -> None:
    print()
    print(f"Нажмите ПРОБЕЛ, чтобы продолжить: {step_title}")
    try:
        # Читаем посимвольно без Enter, но кроссплатформенно проще ждать Enter.
        # Для UX — принимаем и пробел, и Enter.
        user_input = input()
        # Если пользователь ввёл не только пробел — просто продолжаем.
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")
        sys.exit(0)


def pretty_rule(title: str) -> None:
    print("\n" + title)
    print("=" * len(title))


def show_table(headers: List[str], rows: List[List[str]], max_rows: int = 20) -> None:
    if not rows:
        print("(нет данных)")
        return
    
    total_rows = len(rows)
    is_truncated = total_rows > max_rows
    displayed_rows = rows[:max_rows]
    
    widths = [len(h) for h in headers]
    for r in displayed_rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(str(cell)))
    def fmt_row(values: List[str]) -> str:
        return " | ".join(str(v).ljust(widths[i]) for i, v in enumerate(values))
    sep = "-+-".join("-" * w for w in widths)
    
    # Показываем заголовок статуса таблицы ПЕРЕД таблицей
    if is_truncated:
        print(f"📋 Таблица (показаны первые {max_rows} из {total_rows} строк):")
    else:
        print(f"📋 Таблица (все {total_rows} строк):")
    
    print(fmt_row(headers))
    print(sep)
    for r in displayed_rows:
        print(fmt_row(r))
    
    # Дополнительное напоминание ПОСЛЕ таблицы для обрезанных таблиц
    if is_truncated:
        print(f"... (показаны первые {max_rows} из {total_rows} строк)")


def main() -> None:
    pretty_rule("Шаг 0. Загрузка конфигурации и инициализация пайплайна")
    # Инициализируем унифицированный пайплайн (ЛУЧШАЯ ПРАКТИКА)
    pipeline = SpanishTextPipeline(min_word_length=config.get_min_word_length())
    
    print(f"Путь к config.yaml: {config.config_path}")
    print(f"spaCy модель: {config.get_spacy_model()}")
    print(f"Минимальная длина слова: {config.get_min_word_length()}")
    print(f"Папка результатов: {config.get_results_folder()}")
    pause("перейти к исходному тексту")

    pretty_rule("Шаг 1. Исходный текст")
    print(TEST_TEXT)
    pause("перейти к комплексному анализу")

    pretty_rule("Шаг 2. Комплексный анализ текста (с сохранением контекста)")
    print("🔍 Анализируем весь текст целиком через spaCy...")
    context = pipeline.analyze_text(TEST_TEXT)
    
    # Получаем только валидные токены
    valid_tokens = pipeline.get_filtered_tokens(context)
    print(f"✅ Обработано: {len(context.tokens)} токенов, {len(valid_tokens)} валидных")
    print(f"⏱️ Время обработки: {context.processing_time_ms:.1f} мс")
    print(f"📖 Предложений: {len(context.sentences)}")
    
    # Показываем примеры токенов для понимания
    print("\n📝 Примеры корректных токенов (используются в анализе):")
    valid_examples = valid_tokens[:5]
    for token in valid_examples:
        print(f"   ✓ '{token.text}' (POS: {token.pos}, лемма: {token.lemma})")
    
    print("\n🚫 Примеры отфильтрованных токенов (не используются):")
    filtered_out = [t for t in context.tokens if not t.is_valid][:5]
    for token in filtered_out:
        reason = []
        if not token.is_alpha:
            reason.append("не буквы")
        punct_chars = ".,!?;:"
        if token.text.strip() in punct_chars:
            reason.append("пунктуация")
        if not token.text.strip():
            reason.append("пробел")
        if len(token.text) < pipeline.min_word_length:
            reason.append(f"< {pipeline.min_word_length} символов")
        reason_str = ", ".join(reason) if reason else "отфильтрован"
        print(f"   ✗ '{token.text}' ({reason_str})")
    
    pause("перейти к детальному разбору")

    pretty_rule("Шаг 3. Детальный разбор: POS, Род, Лемма")
    pos_tagger = POSTagger(model_name=config.get_spacy_model())  # Для перевода POS на русский
    
    rows = []
    for i, token in enumerate(valid_tokens, start=1):
        gender = token.morph.get('Gender', [None])[0] if 'Gender' in token.morph else None
        rows.append([
            str(i), 
            token.text, 
            token.pos, 
            pos_tagger.get_pos_tag_ru(token.pos), 
            gender or "-",
            token.lemma
        ])
    
    show_table(["#", "Токен", "POS", "POS (RU)", "Gender", "Лемма"], rows)
    pause("перейти к лемматизации с артиклями")

    pretty_rule("Шаг 4. Лемматизация с артиклями (как будет в финальном результате)")
    print("🔍 Показываем, как леммы форматируются для экспорта в Excel:")
    
    lemma_rows = []
    for i, token in enumerate(valid_tokens, start=1):
        gender = token.morph.get('Gender', [None])[0] if 'Gender' in token.morph else None
        if token.pos == 'NOUN':
            excel_format = pipeline.format_noun_with_article(token.lemma, gender)
        else:
            excel_format = token.lemma
        
        lemma_rows.append([
            str(i), 
            token.text, 
            token.lemma,
            excel_format,
            gender or "-"
        ])
    
    show_table(["#", "Токен", "Лемма", "Формат для Excel", "Род"], lemma_rows)
    print("\n💡 Примечание: в колонке 'Формат для Excel' существительные показаны с артиклями")
    pause("перейти к частотному анализу")

    pretty_rule("Шаг 5. Частотный анализ (NOUN с артиклем по роду, остальные — по лемме)")
    freq = FrequencyAnalyzer()
    
    # Применяем правила проекта с контекстной информацией
    freq_tokens = []
    for token in valid_tokens:
        if token.pos == 'NOUN':
            # Используем метод пайплайна для форматирования с артиклем
            gender = token.morph.get('Gender', [None])[0] if 'Gender' in token.morph else None
            key = pipeline.format_noun_with_article(token.lemma, gender)
        else:
            # Для остальных частей речи используем лемму
            key = token.lemma
        freq_tokens.append(key)
    
    freq_map = freq.count_frequency(freq_tokens)
    most_common = freq.get_most_frequent(20)
    print(f"Уникальных ключей частотности: {len(freq_map)}")
    show_table(["Ключ частотности", "Частота"], [[w, str(c)] for w, c in most_common])
    
    # Покажем примеры контекста для частых слов
    print("\n📖 Примеры контекста для топ-слов:")
    for freq_key, count in most_common[:5]:
        # Находим первый токен с этим ключом
        for token in valid_tokens:
            token_key = pipeline.format_noun_with_article(token.lemma, 
                token.morph.get('Gender', [None])[0] if 'Gender' in token.morph else None) if token.pos == 'NOUN' else token.lemma
            if token_key == freq_key:
                ctx = pipeline.get_context_around_token(context, token, window=3)
                print(f"  {freq_key}: ...{ctx}...")
                break
    
    pause("перейти к сборке итогового результата")

    pretty_rule("Шаг 6. Сборка итогового результата (как в Excel экспорте)")
    print("📋 Формируем финальную таблицу с артиклями для существительных:")
    
    # Создаём результат как в реальном анализаторе
    final_rows = []
    for i, token in enumerate(valid_tokens, start=1):
        gender = token.morph.get('Gender', [None])[0] if 'Gender' in token.morph else None
        
        # Формат для отображения слова (как в Excel)
        if token.pos == 'NOUN':
            word_display = pipeline.format_noun_with_article(token.lemma, gender)
            freq_key = word_display
        else:
            word_display = token.text
            freq_key = token.lemma
        
        frequency = freq_map.get(freq_key, 0)
        
        final_rows.append([
            str(i),
            word_display,  # Слово с артиклем для NOUN
            token.lemma,
            pos_tagger.get_pos_tag_ru(token.pos),
            gender or "-",
            str(frequency),
            "Нет"  # is_known (для простоты все неизвестные)
        ])
    
    show_table([
        "#", "Слово (для Excel)", "Лемма", "Часть речи", "Род", "Частота", "Известно"
    ], final_rows, max_rows=15)
    
    print("\n💡 Примечание: в колонке 'Слово (для Excel)' существительные показаны с артиклями")
    print("📊 Это именно то, что попадёт в финальный Excel файл")
    pause("перейти к детальной демонстрации работы с ANKI")

    pretty_rule("Шаг 7. Подробная демонстрация логики работы с ANKI")
    print("🔗 Показываем весь процесс интеграции с ANKI: от подключения до поиска слов")
    
    print("\n📋 7.1. Подключение к ANKI через AnkiConnect")
    print("   ⚡ Проверяем доступность AnkiConnect API...")
    
    # Создаём word_comparator для демонстрации
    demo_comparator = WordComparator()
    
    if demo_comparator.anki_connector.is_available():
        print("   ✅ AnkiConnect доступен!")
        
        # Получаем информацию о подключении
        conn_info = demo_comparator.anki_connector.get_connection_info()
        print(f"   📊 Версия AnkiConnect: {conn_info.get('version', 'неизвестна')}")
        print(f"   📚 Всего колод в ANKI: {conn_info.get('total_decks', 0)}")
        print(f"   🇪🇸 Испанских колод: {len(conn_info.get('spanish_decks', []))}")
        
        pause("перейти к извлечению Notes из ANKI")
        
        print("\n📋 7.2. Извлечение Notes (заметок) из испанских колод")
        print("   🔍 Используем запрос: deck:Spanish*")
        print("   📝 ВАЖНО: Работаем с Notes напрямую, а не через Cards!")
        print("   💡 Каждое поле FrontText рассматривается как один термин для изучения")
        
        # Показываем процесс извлечения
        spanish_terms = demo_comparator.known_words
        
        print(f"   ✅ Извлечено {len(spanish_terms)} терминов из ANKI")
        
        # Показываем примеры терминов
        print("\n   📝 Примеры терминов (первые 8):")
        sample_terms = sorted(list(spanish_terms))[:8]
        for i, term in enumerate(sample_terms, 1):
            print(f"      {i:2d}. \"{term}\"")
        
        # Статистика типов терминов
        phrases = [t for t in spanish_terms if ' ' in t]
        single_words = [t for t in spanish_terms if ' ' not in t]
        print(f"\n   📊 Статистика терминов:")
        print(f"      🔤 Отдельных слов: {len(single_words)}")
        print(f"      📖 Фраз: {len(phrases)} (например: 'comprar un billete', 'abrir la puerta')")
        
        pause("перейти к демонстрации логики поиска")
        
        print("\n📋 7.3. Логика определения известности слов (СТРОГО)")
        print("   🎯 Демонстрируем как проверяется известность:")
        print("   1️⃣ Точное совпадение с термином в ANKI")
        print("   🚫 Вхождение слова во фразу НЕ считается известностью")
        
        # Тестовые примеры для демонстрации
        demo_words = [
            ("conductor", "отдельное слово"),
            ("el conductor", "слово с артиклем"),
            ("comprar", "слово из фразы"),
            ("billete", "слово из фразы"),
            ("especial", "неизвестное слово"),
        ]
        
        demo_rows = []
        for word, description in demo_words:
            is_known = demo_comparator.is_word_known(word)
            
            # Ищем в каких терминах ANKI встречается это слово
            found_examples = []
            
            # Точное совпадение
            if word.lower() in spanish_terms:
                found_examples.append(f"[точное] '{word.lower()}'")
            
            # Для прозрачности можем указать, что слово встречается внутри фраз
            import re
            pattern = r'\\b' + re.escape(word.lower()) + r'\\b'
            phrase_hits = [term for term in sorted(spanish_terms) if ' ' in term and re.search(pattern, term)]
            if phrase_hits and word.lower() not in spanish_terms:
                found_examples.append("(встречается внутри фраз — не считается)")
            
            found_text = "; ".join(found_examples) if found_examples else "—"
            status = "✅ Известно" if is_known else "❌ Неизвестно"
            
            demo_rows.append([word, description, status, found_text[:60] + "..." if len(found_text) > 60 else found_text])
        
        show_table([
            "Слово", "Тип", "Статус", "Найдено в ANKI"
        ], demo_rows)
        
        pause("перейти к демонстрации поиска похожих слов")
        
        print("\n📋 7.4. Поиск похожих слов для неизвестных терминов")
        print("   🔍 Алгоритм поиска похожих:")
        print("   1️⃣ Точное совпадение (если есть)")
        print("   2️⃣ Слова, начинающиеся с той же основы") 
        print("   3️⃣ Для возвратных глаголов (с 'se') — поиск базовой формы")
        
        # Демонстрируем поиск похожих
        similarity_examples = [
            ("especial", "неизвестное слово"),
            ("ubicar", "возможно есть похожие"),
            ("fantasma", "полностью новое слово"),
        ]
        
        similar_rows = []
        for word, description in similarity_examples:
            is_known = demo_comparator.is_word_known(word)
            similar = demo_comparator.get_similar_candidates(
                lemma=word, pos='NOUN', gender=None
            )
            
            status = "✅ Известно" if is_known else "❌ Неизвестно"
            similar_text = ", ".join(similar[:3]) if similar else "Нет похожих"
            if len(similar) > 3:
                similar_text += f" (+ ещё {len(similar) - 3})"
            
            similar_rows.append([word, description, status, similar_text])
        
        show_table([
            "Слово", "Описание", "Статус", "Похожие в ANKI"
        ], similar_rows)
        
        print("\n💡 Эти 'похожие' слова попадут в комментарии Excel, но НЕ делают слово 'известным'")
        
        pause("перейти к проверке слов из анализируемого текста")
        
    else:
        print("   ⚠️ AnkiConnect недоступен - используем демо-данные")
        
        pause("перейти к проверке слов (демо-режим)")

    pretty_rule("Шаг 8. Проверка конкретных слов из текста в ANKI")
    print("🔍 Используем ТУ ЖЕ логику что и основной анализатор проекта...")
    
    # Создаём WordAnalyzer и инициализируем ANKI интеграцию (как в основном коде)
    analyzer = WordAnalyzer()
    anki_success = analyzer.init_anki_integration()
    
    if anki_success:
        print(f"✅ Используем ту же ANKI интеграцию что и в основном проекте")
        
        # Добавляем наш тестовый текст в анализатор
        analyzer.add_words_from_text(TEST_TEXT)
        
        # Получаем первые 10 слов из анализа
        all_words = list(analyzer.word_frequencies.most_common())[:10]
        
        anki_check_rows = []
        for i, (word_with_pos, freq) in enumerate(all_words, start=1):
            # Извлекаем слово и часть речи из формата "слово (часть_речи)"
            if ' (' in word_with_pos and word_with_pos.endswith(')'):
                word_part = word_with_pos.split(' (')[0]  # "el capital" или "capital"
                pos_tag = word_with_pos.split(' (')[1].rstrip(')')
            else:
                word_part = word_with_pos
                pos_tag = 'неизвестно'
            
            # Используем ТУ ЖЕ логику что в export_to_excel основного анализатора
            is_known = analyzer.word_comparator.is_word_known(word_part)
            
            # Формируем комментарий ТАК ЖЕ как в основном коде
            comment = ""
            if not is_known:
                # Извлекаем базовую лемму для get_similar_candidates
                if word_part.startswith(('el ', 'la ')):
                    base_lemma = word_part.split(' ', 1)[1]
                else:
                    base_lemma = word_part
                
                token_info = analyzer.token_details.get(base_lemma, {})
                similar = analyzer.word_comparator.get_similar_candidates(
                    lemma=base_lemma,
                    pos=token_info.get('pos', 'UNKNOWN'),
                    gender=token_info.get('gender')
                )
                if similar:
                    comment = "Похожие в ANKI: " + ", ".join(similar)
                else:
                    comment = "Новое слово"
            
            anki_check_rows.append([
                str(i),
                word_part,
                "Да" if is_known else "Нет",
                comment or "—"
            ])
    else:
        print("⚠️ ANKI недоступен - показываем демо-данные")
        anki_check_rows = [
            ["1", "la casa", "Нет", "Демо-режим"],
            ["2", "muy", "Нет", "Демо-режим"],
            ["3", "grande", "Нет", "Демо-режим"]
        ]
    
    show_table([
        "#", "Слово", "Известно в ANKI", "Комментарий для Excel"
    ], anki_check_rows)
    
    print("\n💡 Примечание: колонка 'Комментарий для Excel' попадёт в финальный экспорт")
    pause("перейти к демонстрации решения проблемы с 'capital'")

    pretty_rule("Шаг 9. Демонстрация решения проблемы омонимов (capital)")
    print("🎯 Показываем, как правильно различается 'la capital' и 'el capital':")
    
    capital_tokens = [t for t in valid_tokens if 'capital' in t.text]
    for i, token in enumerate(capital_tokens, 1):
        gender = token.morph.get('Gender', [None])[0] if 'Gender' in token.morph else None
        formatted = pipeline.format_noun_with_article(token.lemma, gender)
        ctx = pipeline.get_context_around_token(context, token, window=4)
        
        print(f"\n{i}. Токен: '{token.text}'")
        print(f"   Лемма: {token.lemma}")
        print(f"   POS: {token.pos} ({pos_tagger.get_pos_tag_ru(token.pos)})")
        print(f"   Род: {gender or 'Неизвестен'}")
        print(f"   Ключ частотности: '{formatted}'")
        print(f"   Контекст: ...{ctx}...")
    
    pause("перейти к обработке имен собственных")

    pretty_rule("Шаг 10. Обработка имен собственных (PROPN → NOUN)")
    print("🏛️ Демонстрируем корректировку имен собственных для консолидации:")
    print("💡 Правило проекта: PROPN автоматически ремапятся в NOUN для единообразия")
    
    # Найдем имена собственные в тексте
    propn_tokens = [t for t in valid_tokens if t.pos == 'PROPN']
    
    if propn_tokens:
        print(f"\n📍 Найдено {len(propn_tokens)} имен собственных в тексте:")
        propn_rows = []
        for i, token in enumerate(propn_tokens, 1):
            gender = token.morph.get('Gender', [None])[0] if 'Gender' in token.morph else None
            # Показываем что было и что стало после коррекции
            original_pos = "PROPN"
            corrected_pos = "NOUN"  # По правилам проекта
            
            # Форматирование как существительного
            formatted = pipeline.format_noun_with_article(token.lemma, gender)
            
            propn_rows.append([
                str(i),
                token.text,
                original_pos,
                corrected_pos,
                pos_tagger.get_pos_tag_ru(corrected_pos),
                gender or "Неизвестен",
                formatted
            ])
        
        show_table([
            "#", "Имя собственное", "Исходный POS", "После коррекции", "POS (RU)", "Род", "Итоговый формат"
        ], propn_rows)
        
        print("\n💡 Примечание: Имена собственные обрабатываются как обычные существительные")
        print("🔄 Это позволяет включить их в общую консолидацию по леммам")
    else:
        print("\n❌ В данном тексте нет имен собственных (PROPN)")
        print("💡 Обычно здесь были бы: Madrid → el madrid, España → la españa")
    
    pause("перейти к обработке рода существительных")

    pretty_rule("Шаг 11. Восстановление рода существительных из контекста")
    print("⚖️ Демонстрируем как восстанавливается род, если spaCy его не определил:")
    print("🔍 Алгоритм: ищем ближайший определитель (DET) слева от существительного")
    
    # Создадим примеры с неопределенным родом
    noun_tokens = [t for t in valid_tokens if t.pos == 'NOUN']
    
    gender_examples = []
    for token in noun_tokens:
        original_gender = token.morph.get('Gender', [None])[0] if 'Gender' in token.morph else None
        
        # Симулируем восстановление рода из контекста (как делает pipeline)
        recovered_gender = original_gender
        recovery_method = "Изначально определен spaCy"
        
        if not original_gender:
            # Ищем определитель слева (упрощенная логика для демо)
            token_position = valid_tokens.index(token)
            for j in range(max(0, token_position - 3), token_position):
                prev_token = valid_tokens[j]
                if prev_token.pos == 'DET':
                    if prev_token.text.lower() in ['el', 'un', 'este', 'ese', 'aquel']:
                        recovered_gender = 'Masc'
                        recovery_method = f"Из DET '{prev_token.text}'"
                        break
                    elif prev_token.text.lower() in ['la', 'una', 'esta', 'esa', 'aquella']:
                        recovered_gender = 'Fem'
                        recovery_method = f"Из DET '{prev_token.text}'"
                        break
            
            if not recovered_gender:
                recovery_method = "Не удалось восстановить"
        
        # Форматирование с восстановленным родом
        if recovered_gender:
            article = "el" if recovered_gender == 'Masc' else "la"
            formatted = f"{article} {token.lemma}"
        else:
            formatted = token.lemma
        
        gender_examples.append([
            token.text,
            token.lemma,
            original_gender or "—",
            recovered_gender or "—",
            recovery_method,
            formatted
        ])
    
    # Показываем первые 8 примеров
    show_table([
        "Токен", "Лемма", "Род (spaCy)", "Восстановленный", "Метод", "Итоговый формат"
    ], gender_examples[:8])
    
    print("\n💡 Примечание: если род не удается восстановить, существительное остается без артикля")
    pause("перейти к финальной консолидации")

    pretty_rule("Шаг 12. Финальная консолидация и дедупликация")
    print("🔄 Демонстрируем полный процесс создания финального списка для Excel:")
    print("📋 Шаги консолидации:")
    print("   1️⃣ Группировка по лемме + POS + род")
    print("   2️⃣ Суммирование частот в группах")
    print("   3️⃣ Формирование итогового списка WordInfo")
    print("   4️⃣ Дедупликация по полю 'Word' с сохранением максимального Count")
    
    # Симулируем процесс консолидации как в реальном анализаторе
    from collections import defaultdict
    
    # Шаг 1: Группировка
    print(f"\n🔍 Шаг 1: Группировка {len(valid_tokens)} токенов по лемме+POS+род")
    groups = defaultdict(list)
    
    for token in valid_tokens:
        gender = token.morph.get('Gender', [None])[0] if 'Gender' in token.morph else None
        # Применяем коррекцию PROPN → NOUN
        corrected_pos = 'NOUN' if token.pos == 'PROPN' else token.pos
        
        key = (token.lemma, corrected_pos, gender)
        groups[key].append(token)
    
    print(f"   📊 Получено {len(groups)} уникальных групп")
    
    # Шаг 2: Подсчет частот
    print(f"\n🔍 Шаг 2: Подсчет частот для каждой группы")
    group_stats = []
    
    for (lemma, pos, gender), tokens in list(groups.items())[:10]:  # Показываем первые 10
        count = len(tokens)
        
        # Формируем отображаемое слово
        if pos == 'NOUN':
            display_word = pipeline.format_noun_with_article(lemma, gender)
        else:
            display_word = lemma
        
        group_stats.append([
            display_word,
            lemma,
            pos_tagger.get_pos_tag_ru(pos),
            gender or "—",
            str(count),
            f"{len(tokens)} токенов"
        ])
    
    show_table([
        "Отображаемое слово", "Лемма", "POS (RU)", "Род", "Частота", "Источник"
    ], group_stats)
    
    pause("перейти к демонстрации дедупликации")
    
    # Шаг 3: Создание WordInfo объектов
    print(f"\n🔍 Шаг 3: Создание списка WordInfo (как для экспорта)")
    
    # Создаем примеры с дублями для демонстрации
    demo_words = [
        # Пример дублей для слова "medio"
        WordInfo(word="medio", lemma="medio", pos_tag="NUM", pos_tag_ru="Числительное", 
                frequency=23, is_known=False, gender=None),
        WordInfo(word="el medio", lemma="medio", pos_tag="NOUN", pos_tag_ru="Существительное", 
                frequency=17, is_known=False, gender="Masc"),
        WordInfo(word="medio", lemma="medio", pos_tag="ADJ", pos_tag_ru="Прилагательное", 
                frequency=19, is_known=False, gender=None),
        WordInfo(word="medio", lemma="medio", pos_tag="ADV", pos_tag_ru="Наречие", 
                frequency=1, is_known=False, gender=None),
        # Еще несколько примеров
        WordInfo(word="la casa", lemma="casa", pos_tag="NOUN", pos_tag_ru="Существительное", 
                frequency=5, is_known=False, gender="Fem"),
        WordInfo(word="grande", lemma="grande", pos_tag="ADJ", pos_tag_ru="Прилагательное", 
                frequency=3, is_known=False, gender=None),
    ]
    
    print(f"📝 Исходный список (с дублями): {len(demo_words)} записей")
    
    # Показываем исходный список
    before_dedup = []
    for i, word_info in enumerate(demo_words, 1):
        before_dedup.append([
            str(i),
            word_info.word,
            word_info.pos_tag_ru,
            word_info.gender or "—",
            str(word_info.frequency),
            "Да" if word_info.is_known else "Нет"
        ])
    
    show_table([
        "#", "Word", "POS", "Род", "Count", "Известно"
    ], before_dedup)
    
    print("\n⚠️ ПРОБЛЕМА: Есть дубли по полю 'Word' (например, 'medio' встречается 3 раза)")
    pause("применить дедупликацию")
    
    # Шаг 4: Дедупликация
    print(f"\n🔍 Шаг 4: Дедупликация по полю 'Word' (наша недавняя исправка)")
    print("   📋 Алгоритм:")
    print("   1️⃣ Сортировка по Word (asc), затем по Count (desc)")
    print("   2️⃣ Удаление дублей, сохранение записи с максимальным Count")
    
    # Применяем дедупликацию
    import pandas as pd
    
    # Преобразуем в DataFrame как в реальном коде
    excel_data = []
    for word_info in demo_words:
        excel_data.append({
            'Word': word_info.word,
            'Lemma': word_info.lemma,
            'Part of Speech': word_info.pos_tag_ru,
            'Gender': word_info.gender or '-',
            'Count': word_info.frequency,
            'Comments': 'Новое слово'
        })
    
    df = pd.DataFrame(excel_data)
    
    print(f"\n📊 ДО дедупликации: {len(df)} строк")
    
    # Применяем ту же логику что в word_analyzer.py
    before_count = len(df)
    df = df.sort_values(['Word', 'Count'], ascending=[True, False], kind='stable')
    df = df.drop_duplicates(subset=['Word'], keep='first').reset_index(drop=True)
    after_count = len(df)
    
    print(f"📊 ПОСЛЕ дедупликации: {len(df)} строк (удалено: {before_count - after_count})")
    
    # Показываем финальный результат
    after_dedup = []
    for i, (_, row) in enumerate(df.iterrows(), 1):
        after_dedup.append([
            str(i),
            row['Word'],
            row['Part of Speech'],
            row['Gender'],
            str(row['Count']),
            row['Comments']
        ])
    
    show_table([
        "#", "Word", "POS", "Род", "Count", "Комментарии"
    ], after_dedup)
    
    print("\n✅ РЕЗУЛЬТАТ: Для 'medio' осталась только запись с максимальным Count (23)")
    print("✅ Каждое уникальное значение Word представлено только один раз")
    print("✅ Это именно то, что попадет в финальный Excel файл")
    
    pause("завершить демо")

    pretty_rule("🎉 ИТОГИ ДЕМОНСТРАЦИИ")
    print("Мы подробно изучили весь процесс формирования финального списка слов:")
    print()
    print("✅ Анализ текста через spaCy с сохранением контекста")
    print("✅ Коррекция POS: PROPN → NOUN для унификации")
    print("✅ Восстановление рода существительных из определителей")
    print("✅ Формирование артиклей: el/la + лемма для NOUN")
    print("✅ Консолидация по группам (лемма + POS + род)")
    print("✅ Интеграция с ANKI для определения известности")
    print("✅ Дедупликация по полю Word с сохранением max Count")
    print()
    print("🔄 Процесс полностью соответствует правилам проекта:")
    print("   📖 Один алгоритм — одно место в коде")
    print("   🎯 Надежная обработка омонимов (la capital ≠ el capital)")
    print("   🔧 Консистентная логика во всех компонентах")


if __name__ == "__main__":
    main()


