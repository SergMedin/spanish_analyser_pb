from typing import Iterable, List, Dict, Any, Set, Optional


class MockAnkiIntegration:
    """Простой мок Anki-интеграции для тестов.

    Позволяет имитировать подключение, поиск заметок и извлечение текста.
    """

    def __init__(self, known_words: Optional[Iterable[str]] = None) -> None:
        self._connected = True
        self._known_words: Set[str] = set(known_words or [])

    # API, совместимый с WordAnalyzer.load_known_words_from_anki
    def is_connected(self) -> bool:
        return self._connected

    def find_notes_by_deck(self, deck_pattern: str) -> List[int]:
        # Возвращаем фиктивные идентификаторы заметок
        return [1, 2, 3]

    def extract_text_from_notes(self, note_ids: List[int], field_names: List[str]) -> List[Dict[str, Any]]:
        # Генерируем фиктивные наборы текстов на основе известных слов
        texts: List[str] = []
        for word in sorted(self._known_words):
            texts.append(f"El {word} está en la casa.")
        return [{"note_id": nid, "texts": texts} for nid in note_ids]


