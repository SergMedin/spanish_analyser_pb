"""
Обёртка над spaCy, реализующая интерфейс BaseTextModel.
"""

from __future__ import annotations

import time
from typing import Dict, Any, Optional, List

try:
    import spacy
except Exception:  # pragma: no cover
    spacy = None  # type: ignore

from .base_model import BaseTextModel, Token, ModelAnalysisResult


class SpacyModel(BaseTextModel):
    """Модель spaCy в унифицированном интерфейсе."""

    def __init__(self, model_name: str = "es_core_news_md") -> None:
        self.model_name = model_name
        self._nlp = None

    def load(self) -> None:
        if self._nlp is not None:
            return
        if spacy is None:
            raise RuntimeError("Библиотека spaCy не установлена. Установите: pip install spacy")
        try:
            self._nlp = spacy.load(self.model_name)
        except Exception as e:
            raise RuntimeError(
                f"Не удалось загрузить модель spaCy '{self.model_name}'. "
                f"Установите модель: python -m spacy download {self.model_name}"
            ) from e

    def analyze_text(self, text: str) -> ModelAnalysisResult:
        start = time.time()
        if not text:
            return ModelAnalysisResult(tokens=[], processing_time_ms=0.0, model_name=self.model_name, model_type="spacy")
        if self._nlp is None:
            self.load()
        doc = self._nlp(text)
        tokens: List[Token] = []
        for token in doc:
            if not token.text.strip():
                continue
            tokens.append(Token(text=token.text, lemma=token.lemma_, pos=token.pos_))
        elapsed = (time.time() - start) * 1000.0
        return ModelAnalysisResult(tokens=tokens, processing_time_ms=elapsed, model_name=self.model_name, model_type="spacy")

    def unload(self) -> None:
        self._nlp = None

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "name": self.model_name,
            "type": "spacy",
            "loaded": self._nlp is not None,
        }


