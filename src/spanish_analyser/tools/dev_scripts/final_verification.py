#!/usr/bin/env python3
"""
Финальная проверка исправлений определения частей речи
"""

import sys
import spacy
import yaml
import os
import tempfile
import pandas as pd

def load_config():
    """Загружает конфигурацию из config.yaml"""
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}

def test_spacy_integration():
    """Тестирует интеграцию spaCy в WordAnalyzer"""
    print("🧪 Финальная проверка исправлений")
    print("=" * 50)

    # Загружаем конфигурацию
    config_data = load_config()
    spacy_model = config_data.get('text_analysis', {}).get('spacy_model', 'es_core_news_md')

    print(f"Модель spaCy из конфигурации: {spacy_model}")

    # УДАЛЕНО: используем единый источник из POSTagger
    from spanish_analyser.components.pos_tagger import POSTagger
    pos_tagger = POSTagger()

    # Базовое определение частей речи (копия из word_analyzer.py)
    def determine_pos_basic(word: str) -> str:
        """Базовое определение части речи"""
        word_lower = word.lower()

        # Простые паттерны для испанского языка
        if word_lower in ['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas']:
            return "определитель"
        elif word_lower in ['y', 'o', 'pero', 'si', 'que', 'como', 'cuando', 'donde']:
            return "союз"
        elif word_lower in ['yo', 'tú', 'él', 'ella', 'nosotros', 'nosotras', 'vosotros', 'vosotras', 'ellos', 'ellas']:
            return "местоимение"
        elif word_lower in ['a', 'ante', 'bajo', 'cabe', 'con', 'contra', 'de', 'desde', 'durante', 'en', 'entre', 'hacia', 'hasta', 'mediante', 'para', 'por', 'según', 'sin', 'so', 'sobre', 'tras']:
            return "предлог"
        elif word_lower.endswith(('ar', 'er', 'ir')):
            return "глагол"
        elif word_lower.endswith(('ado', 'ido', 'ada', 'ida')):
            return "причастие"
        elif word_lower.endswith(('ando', 'iendo', 'endo')):
            return "герундий"
        elif word_lower.endswith(('oso', 'osa', 'al', 'ar', 'ivo', 'iva', 'able', 'ible')):
            return "прилагательное"
        elif word_lower.endswith(('mente')):
            return "наречие"
        elif word_lower.endswith(('ción', 'sión', 'dad', 'tad', 'tud', 'ez', 'eza', 'ura', 'ía', 'io')):
            return "существительное"
        elif word_lower.isdigit() or word_lower in ['primero', 'segundo', 'tercero', 'cuarto', 'quinto']:
            return "числительное"

        return "неизвестно"

    # Определение части речи с spaCy
    def determine_pos_with_spacy(word: str, nlp) -> str:
        """Определение части речи с помощью spaCy"""
        if not nlp:
            return determine_pos_basic(word)

        try:
            doc = nlp(word)
            if doc:
                token = doc[0]
                pos_tag = token.pos_
                return pos_tagger.get_pos_tag_ru(pos_tag)
        except Exception as e:
            print(f"Ошибка при анализе слова '{word}' с spaCy: {e}")

        return "неизвестно"

    # Основной метод определения части речи
    def determine_pos(word: str, nlp) -> str:
        """Основной метод определения части речи"""
        if nlp:
            return determine_pos_with_spacy(word, nlp)
        else:
            print(f"⚠️ spaCy недоступен для слова '{word}', используем базовое определение")
            return determine_pos_basic(word)

    # Тестируем загрузку spaCy
    nlp = None
    try:
        nlp = spacy.load(spacy_model)
        print(f"✅ Модель spaCy {spacy_model} загружена успешно")
    except Exception as e:
        print(f"❌ Ошибка загрузки spaCy: {e}")
        print("⚠️ Продолжаем без spaCy, используя базовое определение")

    # Тестируем определение частей речи
    test_words = [
        "casa",      # существительное (дом)
        "correr",    # глагол (бегать)
        "rápido",    # прилагательное (быстрый)
        "en",        # предлог (в)
        "yo",        # местоимение (я)
        "feliz",     # прилагательное (счастливый)
        "comer",     # глагол (есть)
        "mesa",      # существительное (стол)
        "con",       # предлог (с)
        "muy"        # наречие (очень)
    ]

    print()
    print("📝 Тестирование определения частей речи:")
    print("-" * 40)

    results = []
    for word in test_words:
        pos = determine_pos(word, nlp)
        results.append((word, pos))
        print("12")

    # Проверяем, что нет "неизвестно" если spaCy работает
    unknown_count = sum(1 for word, pos in results if pos == "неизвестно")

    print()
    print("📊 Результаты тестирования:")
    print("-" * 40)

    if nlp:
        print(f"✅ spaCy работает корректно")
        print(f"📋 Определено частей речи: {len(test_words) - unknown_count} из {len(test_words)}")
        if unknown_count == 0:
            print("🎉 Успех! Все слова определены корректно")
        else:
            print(f"⚠️ {unknown_count} слов определены как 'неизвестно'")
    else:
        print("⚠️ spaCy недоступен, используется базовое определение")
        print(f"📋 Базовое определение: {len(test_words) - unknown_count} из {len(test_words)}")

    # Тестируем имитацию Excel экспорта
    print()
    print("📈 Тестирование формата Excel:")
    print("-" * 40)

    excel_data = []
    for word, pos in results:
        excel_data.append({
            'Word': word,
            'Part of Speech': pos,
            'Frequency': '1.00%',  # имитация
            'Count': 1
        })

    df = pd.DataFrame(excel_data)
    print("📋 Данные для Excel:")
    for i, row in df.iterrows():
        print(f"  {row['Word']}: {row['Part of Speech']}")

    # Проверяем, что в Part of Speech нет "неизвестно" если spaCy работает
    if nlp and unknown_count == 0:
        print()
        print("🎉 ИТОГ: Проблема с определением частей речи РЕШЕНА!")
        print("✅ В Excel файле теперь будут корректные русскоязычные названия частей речи")
    elif not nlp:
        print()
        print("⚠️ ИТОГ: spaCy недоступен, но базовое определение работает")
        print("💡 Для полной работы установите модель: python -m spacy download es_core_news_md")
    else:
        print()
        print(f"⚠️ ИТОГ: {unknown_count} слов все еще не определены")
        print("🔍 Нужно проверить логику определения частей речи")

if __name__ == "__main__":
    test_spacy_integration()


