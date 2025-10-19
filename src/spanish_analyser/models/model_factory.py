"""
Фабрика для создания текстовых моделей по конфигурации.
"""

from __future__ import annotations

from typing import Optional, Dict, Any

from .base_model import BaseTextModel
from .spacy_model import SpacyModel


class ModelFactory:
    """Создаёт модели на основе конфигурации."""

    @staticmethod
    def create(model_cfg: Dict[str, Any]) -> Optional[BaseTextModel]:
        """Создаёт модель из словаря настроек.

        Ожидаемый формат:
        {
          "type": "spacy",
          "name": "es_core_news_md",
          # Доп.поля для конкретных моделей
        }
        """
        if not model_cfg:
            return None
        model_type = (model_cfg.get("type") or "").lower()
        name = model_cfg.get("name") or ""
        if model_type == "spacy":
            model_name = name or "es_core_news_md"
            return SpacyModel(model_name=model_name)
        return None

    @staticmethod
    def create_and_load_or_fail(model_cfg: Dict[str, Any]) -> BaseTextModel:
        """Создаёт и загружает модель или выбрасывает ошибку (Fail Fast).

        Args:
            model_cfg: Конфигурация модели

        Returns:
            Загруженная модель

        Raises:
            RuntimeError: если модель не может быть создана или загружена
        """
        model = ModelFactory.create(model_cfg)
        if model is None:
            raise RuntimeError("Некорректная конфигурация модели: отсутствует или неизвестный тип")
        try:
            model.load()
            return model
        except Exception as e:
            raise RuntimeError(f"Не удалось загрузить модель: {e}")


