#!/usr/bin/env python3
"""
Инструмент для расследования слов в системе анализа (CLI).
Перемещён из корня проекта в `tools/text_analyzer/` для порядка структуры.
"""

import sys
from pathlib import Path

# Обеспечиваем доступ к пакету из src независимо от текущей директории запуска
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from spanish_analyser.config import config  # noqa: E402
from spanish_analyser.components.anki_connector import AnkiConnector  # noqa: E402
import re  # noqa: E402


class WordInvestigator:
    """Класс для исследования слов"""

    def __init__(self):
        self.config = config
        self.anki = None
        self.downloads_path = Path(self.config.get_downloads_folder())

    def connect_to_anki(self):
        """Проверка доступности AnkiConnect"""
        print("🔗 Проверка AnkiConnect...")
        self.anki = AnkiConnector()
        if self.anki.is_available():
            print("✅ AnkiConnect доступен")
            return True
        else:
            print("❌ AnkiConnect недоступен")
            return False

    def search_word_in_html_files(self, word: str):
        """Быстрый поиск слова в HTML файлах (без лемматизации)"""
        print(f"\n🔍 Поиск слова '{word}' в HTML файлах:")

        found_files = []
        total_occurrences = 0

        html_files = list(self.downloads_path.glob("*.html"))
        total_files = len(html_files)
        print(f"📁 Проверяю {total_files} HTML файлов...")

        target = word.lower()

        for i, html_file in enumerate(html_files):
            try:
                if total_files and (i % 50 == 0 or i == total_files - 1):
                    progress = (i + 1) / total_files * 100
                    print(f"   🔍 Поиск: {i + 1}/{total_files} ({progress:.1f}%)")
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()

                count = content.count(target)
                if count > 0:
                    found_files.append((html_file.name, count))
                    total_occurrences += count
            except Exception as e:
                print(f"⚠️ Ошибка при чтении {html_file.name}: {e}")

        if found_files:
            print(f"✅ Слово '{word}' найдено в {len(found_files)} файлах")
            print(f"📊 Общее количество вхождений: {total_occurrences}")
            found_files.sort(key=lambda x: x[1], reverse=True)
            print(f"\n📂 Топ файлов по количеству вхождений:")
            for i, (filename, count) in enumerate(found_files[:5]):
                print(f"   {i+1}. {filename}: {count} раз")
            self._show_word_context(found_files[0][0], word)
        else:
            print(f"❌ Слово '{word}' не найдено в HTML файлах")

        return total_occurrences, len(found_files)

    def _show_word_context(self, filename: str, word: str):
        """Показать небольшой контекст слова из файла"""
        print(f"\n📝 Контекст из файла {filename}:")
        filepath = self.downloads_path / filename
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            match = pattern.search(content)
            if match:
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(context, 'html.parser')
                clean_context = soup.get_text(separator=" ", strip=True)
                print(f"   ...{clean_context}...")
        except Exception as e:
            print(f"⚠️ Ошибка при извлечении контекста: {e}")

    def check_word_in_anki(self, word: str):
        """Прямой быстрый поиск слова в Anki"""
        print(f"\n🔍 Поиск слова '{word}' в Anki:")
        if not self.anki:
            print("❌ Подключение к Anki отсутствует")
            return []
        try:
            decks = self.anki.find_spanish_decks("Spanish")
            found = []
            for deck in decks:
                card_ids = self.anki.get_cards_from_deck(deck)
                cards_info = self.anki.get_cards_info(card_ids)
                note_ids = [c.get('note') for c in cards_info if c.get('note')]
                notes_info = self.anki.get_notes_info(note_ids)
                target = word.lower()
                for note in notes_info:
                    fields = note.get('fields', {})
                    for field_name, field_data in fields.items():
                        val = (field_data or {}).get('value', '')
                        if val and target in val.lower():
                            found.append((note.get('noteId'), field_name, val[:120] + ('...' if len(val) > 120 else '')))
                            if len(found) >= 3:
                                break
                    if len(found) >= 3:
                        break
                if len(found) >= 3:
                    break
            if found:
                print(f"✅ Найдено {len(found)} карточек со словом '{word}':")
                for i, (nid, fname, preview) in enumerate(found, 1):
                    print(f"   {i}. noteId={nid} field={fname}: {preview}")
            else:
                print(f"❌ Карточки со словом '{word}' не найдены")
            return found
        except Exception as e:
            print(f"❌ Ошибка при поиске в Anki: {e}")
            return []

    def investigate_word(self, word: str):
        """Быстрое исследование слова (production-режим)"""
        print("=" * 60)
        print(f"🔍 ИССЛЕДОВАНИЕ СЛОВА: '{word}'")
        print("=" * 60)

        # 1) Быстрый поиск в текстах
        html_occurrences, html_files = self.search_word_in_html_files(word)

        # 2) Быстрый поиск в Anki
        anki_cards = self.check_word_in_anki(word)

        # 3) Решение: попадёт ли в выгрузку?
        # В Excel попадают ТОЛЬКО новые слова (которых нет в Anki).
        will_be_exported = html_occurrences > 0 and len(anki_cards) == 0
        status = "Да" if will_be_exported else "Нет"

        print("\n📊 ИТОГ:")
        print(f"   📄 В текстах: {'найдено' if html_occurrences > 0 else 'не найдено'} (вхождений: {html_occurrences})")
        print(f"   📚 В Anki: {'найдено' if anki_cards else 'не найдено'}")
        print(f"   📁 Попадёт в Excel выгрузку: {status}")
        print("=" * 60)

    def run_cli(self, word: str):
        if not self.connect_to_anki():
            return 1
        self.investigate_word(word)
        if self.anki:
            self.anki.disconnect()
            print("✅ Соединение с Anki закрыто")
        return 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Быстрый инструмент для исследования слов')
    parser.add_argument('word', help='Слово для исследования (например, "cúbico")')
    args = parser.parse_args()

    investigator = WordInvestigator()
    raise SystemExit(investigator.run_cli(args.word))


if __name__ == '__main__':
    main()





