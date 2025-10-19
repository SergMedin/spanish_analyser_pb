"""
Хелпер для генерации BackText через OpenAI API.

Особенности реализации:
- Шаблон промпта хранится в текстовом файле (`prompt_templates/anki_backtext_prompt_ru.txt`).
- В шаблоне используется плейсхолдер `{{TERM}}`, который заменяется на целевое слово/фразу для запроса к ИИ.
- Ожидание: модель возвращает только HTML (без бэктиков/пояснений). Мы дополнительно валидируем минимум тегов.
- Ключ берётся из переменной окружения `OPENAI_API_KEY`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from openai import OpenAI
import time
from spanish_analyser.config import config  # type: ignore
from spanish_analyser.cache import CacheManager  # type: ignore
import logging


class QuotaExceededError(Exception):
    """Исключение для случаев превышения квоты OpenAI API."""
    pass


PROMPT_PATH = Path(__file__).parent / "prompt_templates" / "anki_backtext_prompt_ru.txt"


def _read_prompt_template() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()


def _basic_html_sanity_check(html: str) -> bool:
    # Простая проверка наличия минимум базовых тегов и отсутствия бэктиков.
    if "```" in html:
        return False
    # Желательно наличие <body> или хотя бы одного тега из набора
    needles = ("<html", "<body", "<strong", "<small", "Sinónimos:", "Synonyms:")
    return any(n in html for n in needles)


# Начиная с новой версии: FrontText задаётся вызывающим кодом (например, значением колонки Word из Excel),
# BackText — полный HTML-ответ модели, валидируемый на базовом уровне.


logger = logging.getLogger(__name__)


def generate_front_and_back(term_for_prompt: str, front_text: Optional[str] = None, model: Optional[str] = None, pos: Optional[str] = None) -> Tuple[str, str]:
    """Генерирует пару (FrontText, BackTextHTML).

    - FrontText: текст для лицевой стороны карточки (обычно это значение из колонки Word экспортa Excel).
    - BackText: полный HTML-ответ модели по шаблону, с `{{TERM}}` заменённым на `term_for_prompt`.

    Args:
        term_for_prompt: слово для перевода (например, "deber"), которое подставляется вместо `{{TERM}}` в шаблоне.
        front_text: явное значение для FrontText (если не задано — используется `term_for_prompt`).
        model: опциональная модель, по умолчанию берётся из окружения `OPENAI_MODEL` или config.
        pos: часть речи на русском языке (например, "глагол"), добавляется в конец промпта для контекста.

    Returns:
        Кортеж: (front_text, back_text_html).
    """
    # Определяем модель (приоритет: аргумент -> env OPENAI_MODEL -> config ai.model)
    model_name = (model or os.environ.get("OPENAI_MODEL") or config.get_ai_model()).strip()
    if os.environ.get("SPANISH_ANALYSER_DEBUG") == "1":
        print(f"[DEBUG] Using model name resolved to: '{model_name}'")

    # Нормализуем вход и формируем ключ кэша вида: openai_anki:<model>:<word>:<pos>
    # Включение части речи в ключ важно, так как перевод может отличаться для разных POS
    word_norm = (term_for_prompt or "").strip()
    front_text_resolved = (front_text or word_norm).strip()
    pos_norm = (pos or "unknown").strip().lower()
    cache_key = f"openai_anki:{model_name}:{word_norm}:{pos_norm}"
    
    # Используем общий кэш-менеджер, который автоматически направит ключи в правильный пул
    cache = CacheManager.get_cache()

    # 1) Попытка взять из кэша до любых обращений к OpenAI
    try:
        cached = cache.get(cache_key)
        if cached and isinstance(cached, (tuple, list)) and len(cached) == 2:
            if os.environ.get("SPANISH_ANALYSER_DEBUG") == "1":
                print(f"[DEBUG] Cache HIT for key: {cache_key}")
            return str(cached[0]), str(cached[1])
    except Exception as _e:
        # Игнорируем ошибки кэша — продолжаем обычным путём
        pass

    # 2) Готовим промпт и клиента (после промаха кэша)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY не задан. Установите переменную окружения OPENAI_API_KEY для генерации перевода."
        )

    # Поддержка нового шаблона с плейсхолдером {{TERM}} и обратной совместимости
    prompt = _read_prompt_template()
    if "{{TERM}}" in prompt:
        # В {{TERM}} подставляем только слово без части речи
        final_prompt = prompt.replace("{{TERM}}", word_norm)
        # Если есть часть речи, добавляем её в конец промпта для контекста
        if pos and pos.strip() and pos.strip() != "неизвестно":
            final_prompt += f"\n\nКонтекст: часть речи - {pos.strip()}"
    else:
        # Фоллбек на старый способ, когда слово добавлялось в конец промпта
        final_prompt = f"{prompt}\n\nСлово или фраза для перевода: {word_norm}".strip()

    client = OpenAI(api_key=api_key)
    last_err: Exception | None = None
    max_retries = config.get_ai_max_retries()
    max_retry_delay = config.get_ai_max_retry_delay()
    
    for attempt in range(max_retries):
        try:
            if os.environ.get("SPANISH_ANALYSER_DEBUG") == "1":
                print(f"[DEBUG] OpenAI model: {model_name}")
                print(f"[DEBUG] Prompt (first 400 chars):\n{final_prompt[:400]}\n---")
            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a precise bilingual lexicographer who only outputs valid HTML when asked."},
                    {"role": "user", "content": final_prompt},
                ],
            )
            content = (resp.choices[0].message.content or "").strip()
            if os.environ.get("SPANISH_ANALYSER_DEBUG") == "1":
                print(f"[DEBUG] OpenAI raw content (first 400 chars):\n{content[:400]}\n---")
            if not content:
                raise RuntimeError("Пустой ответ от модели OpenAI")
            # Теперь FrontText передаётся явно вызывающим кодом, BackText — весь HTML из ответа
            front, back_html = front_text_resolved, content
            if not _basic_html_sanity_check(back_html):
                raise RuntimeError("Ответ модели не содержит корректного HTML для BackText")
            # 3) Сохраняем в кэш и возвращаем
            try:
                cache.set(cache_key, (front, back_html))
                if os.environ.get("SPANISH_ANALYSER_DEBUG") == "1":
                    print(f"[DEBUG] Cache STORE for key: {cache_key}")
            except Exception:
                pass
            return front, back_html
        except Exception as e:
            last_err = e
            # Улучшенная обработка различных типов ошибок
            if "429" in str(e) or "rate limit" in str(e).lower():
                # Для rate limiting используем экспоненциальную задержку, но ограниченную максимумом
                wait_time = min(max_retry_delay, 2 * (2 ** attempt))
                logger.warning(f"Rate limit достигнут, ждём {wait_time} секунд перед повтором {attempt + 1}/{max_retries}")
                time.sleep(wait_time)
            elif "insufficient_quota" in str(e).lower():
                # При превышении квоты дальнейшие попытки бессмысленны
                logger.error("Превышена квота OpenAI, дальнейшие попытки невозможны")
                raise QuotaExceededError(
                    "Превышена квота OpenAI API. "
                    "Пополните баланс на https://platform.openai.com/account/billing или "
                    "обновите план подписки. Подробности в документации: "
                    "https://platform.openai.com/docs/guides/error-codes/api-errors"
                ) from e
            else:
                # Для других ошибок - небольшая экспоненциальная задержка
                wait_time = min(5, 1 + attempt)
                if attempt < max_retries - 1:  # не спим после последней попытки
                    time.sleep(wait_time)
    
    raise RuntimeError(f"Ошибка при обращении к OpenAI после {max_retries} попыток: {last_err}")
