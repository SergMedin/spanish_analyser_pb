"""
Базовые интерфейсы и структуры данных для текстовых моделей (spaCy).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class Token:
    """Унифицированный токен."""
    text: str
    lemma: str
    pos: str


@dataclass
class ModelAnalysisResult:
    """Результат анализа текста текстовой моделью."""
    tokens: List[Token]
    processing_time_ms: float
    model_name: str
    model_type: str
    metadata: Optional[Dict[str, Any]] = None


class BaseTextModel(ABC):
    """Базовый интерфейс текстовой модели."""

    @abstractmethod
    def load(self) -> None:
        """Загружает модель в память (ленивая загрузка)."""
        pass

    @abstractmethod
    def analyze_text(self, text: str) -> ModelAnalysisResult:
        """Анализирует текст и возвращает унифицированный результат."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Выгружает модель из памяти (если применимо)."""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Возвращает информацию о модели (имя, версия, тип)."""
        pass


