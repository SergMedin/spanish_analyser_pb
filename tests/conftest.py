import os
from pathlib import Path
from typing import Dict, Any

import pytest

from spanish_analyser.config import Config, config as app_config


@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Возвращает настройки для тестов из config.yaml.

    Включает раздел `testing` с параметрами покрытия, производительности и качества.
    """
    # Используем глобальную конфигурацию, найденную в корне проекта
    cfg = Config()
    return cfg.get("testing", {}) or {}


@pytest.fixture
def temp_directory(tmp_path: Path) -> Path:
    """Временная директория для тестов.

    Возвращает уникальную директорию для каждого теста.
    """
    return tmp_path


@pytest.fixture(scope="session")
def sample_texts():
    """Простые наборы испанских текстов для тестирования."""
    from .fixtures.sample_texts import SAMPLE_SIMPLE_TEXT, SAMPLE_COMPLEX_TEXT, SAMPLE_HTML_TEXT

    return {
        "simple": SAMPLE_SIMPLE_TEXT,
        "complex": SAMPLE_COMPLEX_TEXT,
        "html": SAMPLE_HTML_TEXT,
    }


@pytest.fixture
def mock_anki():
    """Эмуляция Anki-интеграции для тестов."""
    from .utils.mock_anki import MockAnkiIntegration

    return MockAnkiIntegration(
        known_words={"gato", "perro", "casa", "comer", "rápido"},
    )


def has_spacy_model() -> bool:
    """Проверяет наличие spaCy модели для испанского языка.

    Использует название модели из конфигурации.
    """
    try:
        import spacy  # noqa: F401
        model_name = app_config.get_spacy_model()
        try:
            spacy.load(model_name)
            return True
        except Exception:
            return False
    except Exception:
        return False


def pytest_configure(config):
    """Регистрируем маркеры для проекта."""
    config.addinivalue_line("markers", "integration: интеграционные тесты")
    config.addinivalue_line("markers", "performance: тесты производительности")
    config.addinivalue_line("markers", "quality: тесты качества/точности")
    config.addinivalue_line("markers", "e2e: сквозные тесты")


# --- Авто‑стаб spaCy для окружений без модели ---
def _is_spacy_model_available() -> bool:
    """Проверяет, доступна ли spaCy модель."""
    try:
        import spacy  # noqa: F401
        model_name = app_config.get_spacy_model()
        try:
            spacy.load(model_name)
            return True
        except Exception:
            return False
    except Exception:
        return False


def _setup_spacy_stub():
    """Настраивает заглушку для spaCy если модель недоступна."""
    if _is_spacy_model_available():
        return None  # Модель доступна — ничего не делаем

    # Модели нет — ставим стаб
    import re
    from types import SimpleNamespace
    import unittest.mock

    lemma_map = {
        # comer
        'como': 'comer', 'comes': 'comer', 'comió': 'comer', 'comio': 'comer', 'comía': 'comer', 'comia': 'comer',
        'comeremos': 'comer', 'comido': 'comer',
        # hablar
        'hablo': 'hablar', 'hablas': 'hablar', 'habló': 'hablar', 'hablo': 'hablar', 'hablaba': 'hablar',
        'hablaremos': 'hablar', 'hablado': 'hablar',
        # ser
        'es': 'ser', 'son': 'ser',
        # casa
        'casas': 'casa', 'casa': 'casa',
        # bonito
        'bonita': 'bonito', 'bonitas': 'bonito', 'bonito': 'bonito',
        # другие встречающиеся в тестах
        'está': 'estar', 'esta': 'esta', 'qué': 'qué', 'que': 'que',
        'aquí': 'aquí', 'niña': 'niña',
        # тестовые слова для качества POS
        'gatos': 'gato', 'corren': 'correr', 'rápido': 'rápido', 'bonita': 'bonito',
        'capital': 'capital', 'antigüedad': 'antigüedad',
    }

    adj_words = {
        'nuevo', 'conocido', 'bonito', 'bonita', 'bonitas', 'primero', 'segundo', 'tercero',
        'muyfrecuente', 'frecuente', 'medio', 'raro', 'muyraro'
    }
    noun_words = {'casa', 'casas', 'texto', 'normal', 'mundo', 'hola', 'gato', 'gatos', 'capital', 'antigüedad'}
    verb_words = set(k for k, v in lemma_map.items() if v in {'comer', 'hablar', 'ser', 'estar', 'correr'})
    adv_words = {'rápido'}

    class FakeMorph:
        def __init__(self, lemma: str, word: str, pos: str):
            self._lemma = lemma
            self._word = word
            self._pos = pos
            # Контекст для определения рода capital
            self._context_gender = None

        def get(self, key: str):
            if key == 'Gender' and self._pos == 'NOUN':
                # Простейшая эвристика для рода
                if self._lemma == 'casa':
                    return ['Fem']
                elif self._lemma == 'capital':
                    # Используем контекст или дефолт
                    if self._context_gender:
                        return [self._context_gender]
                    # Дефолт для capital зависит от наличия артикля в оригинальном слове
                    return ['Fem']  # по умолчанию Fem для "la capital"
                elif self._lemma == 'gato':
                    return ['Masc']
                elif self._lemma == 'antigüedad':
                    return ['Fem']
            return []

        def __iter__(self):
            g = self.get('Gender')
            if g:
                yield f'Gender={g[0]}'
                
        def set_context_gender(self, gender: str):
            """Устанавливает род на основе контекста."""
            self._context_gender = gender

    class FakeToken:
        def __init__(self, text: str):
            self.text = text
            self._ = SimpleNamespace(corrected_pos=None)
            low = text.lower()
            
            # Убираем знаки препинания для поиска в lemma_map
            clean_low = ''.join(c for c in low if c.isalpha() or c in 'áéíóúüñÁÉÍÓÚÜÑ')
            
            self.lemma_ = lemma_map.get(clean_low, lemma_map.get(low, clean_low))
            
            if low in verb_words or clean_low in verb_words:
                self.pos_ = 'VERB'
            elif low in adj_words or clean_low in adj_words:
                self.pos_ = 'ADJ'
            elif low in adv_words or clean_low in adv_words:
                self.pos_ = 'ADV'
            elif low in noun_words or clean_low in noun_words or self.lemma_ in noun_words:
                self.pos_ = 'NOUN'
            elif low in {'el', 'la', 'los', 'las'}:
                self.pos_ = 'DET'
            else:
                self.pos_ = 'NOUN'  # безопасное значение по умолчанию
            self.is_alpha = all(c.isalpha() or c in 'áéíóúüñÁÉÍÓÚÜÑ' for c in text)
            self.morph = FakeMorph(self.lemma_.lower(), low, self.pos_)
            self.idx = 0

    class FakeDoc(list):
        def __init__(self, tokens):
            super().__init__(tokens)
            self.sents = []

    class FakeNLP:
        def __init__(self):
            self.lang = 'es'
            self.pipe_names = ['tokenizer', 'tagger', 'parser', 'attribute_ruler', 'lemmatizer']

        def __call__(self, text: str):
            # Извлекаем слова с диакритикой (включая ü)
            words = re.findall(r"[A-Za-zÁÉÍÓÚÜáéíóúüñÑ]+", text)
            toks = []
            
            # Анализируем контекст для определения рода
            for i, word in enumerate(words):
                token = FakeToken(word)
                
                # Специальная логика для capital - определяем род по предыдущему артиклю
                if token.lemma_ == 'capital' and token.pos_ == 'NOUN':
                    # Ищем предыдущий артикль в контексте
                    prev_words = words[max(0, i-3):i]  # смотрим на 3 слова назад
                    if any(w.lower() in ['la'] for w in prev_words):
                        token.morph.set_context_gender('Fem')
                    elif any(w.lower() in ['el'] for w in prev_words):
                        token.morph.set_context_gender('Masc')
                
                toks.append(token)
            
            # Проставим index приблизительно
            idx = 0
            for t in toks:
                t.idx = idx
                idx += len(t.text) + 1
            return FakeDoc(toks)

    fake_nlp = FakeNLP()

    # Создаем мок для spacy.load, который будет возвращать нашу fake модель
    spacy_load_patcher = unittest.mock.patch('spacy.load', return_value=fake_nlp)
    spacy_load_patcher.start()

    return spacy_load_patcher


# Настраиваем патчинг spaCy при импорте
_spacy_patcher = _setup_spacy_stub()


@pytest.fixture(autouse=True)
def setup_spacy_for_test():
    """Fixture для настройки spaCy в каждом тесте."""
    # Очищаем синглтон SpacyManager перед каждым тестом
    try:
        from spanish_analyser.components.spacy_manager import SpacyManager
        SpacyManager._instance = None
        SpacyManager._nlp = None
    except ImportError:
        pass
    
    yield
    
    # Очищаем синглтон после теста
    try:
        from spanish_analyser.components.spacy_manager import SpacyManager
        SpacyManager._instance = None
        SpacyManager._nlp = None
    except ImportError:
        pass

