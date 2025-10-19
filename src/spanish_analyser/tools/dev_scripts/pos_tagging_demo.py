#!/usr/bin/env python3
"""
Тестовый скрипт для проверки определения частей речи
"""

import sys
sys.path.append('src')

import spacy
import yaml
import os

# Загружаем конфигурацию напрямую
def load_config():
    """Загружает конфигурацию из config.yaml"""
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}

config_data = load_config()
spacy_model = config_data.get('text_analysis', {}).get('spacy_model', 'es_core_news_md')

def test_spacy_directly():
    """Тестирует spaCy напрямую"""
    print("🧪 Тестирование spaCy напрямую")
    print("=" * 50)

    # Загружаем модель spaCy
    print(f"Загружаем модель: {spacy_model}")

    try:
        nlp = spacy.load(spacy_model)
        print(f"✅ Модель {spacy_model} загружена успешно")
    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        return

    # УДАЛЕНО: используем единый источник из POSTagger
    from spanish_analyser.components.pos_tagger import POSTagger
    pos_tagger = POSTagger()

    # Тестовые слова на испанском
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
    print("📝 Тестирование отдельных слов:")
    print("-" * 30)

    for word in test_words:
        try:
            doc = nlp(word)
            if doc:
                token = doc[0]
                pos_tag = token.pos_
                pos_name = pos_tagger.get_pos_tag_ru(pos_tag)
                print("12")
            else:
                print("12")
        except Exception as e:
            print("12")

    print()
    print("📊 Тестирование анализа текста:")
    print("-" * 30)

    # Тестовый текст
    test_text = "La casa es muy grande. Yo corro rápido en el parque."
    print(f"Текст: {test_text}")
    print()

    # Анализируем текст
    doc = nlp(test_text)

    print("Слова с частями речи:")
    for token in doc:
        if token.is_alpha:
                            pos_name = pos_tagger.get_pos_tag_ru(token.pos_)
            print(f"  {token.text}: {pos_name} (лемма: {token.lemma_})")

if __name__ == "__main__":
    test_spacy_directly()
