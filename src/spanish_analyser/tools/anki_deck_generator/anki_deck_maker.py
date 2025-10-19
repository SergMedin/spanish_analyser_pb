#!/usr/bin/env python3
"""
Интерактивный инструмент для генерации .apkg (Anki deck package) из последнего Excel-отчёта

Задачи инструмента:
- Найти последний Excel-файл с результатами частотного анализа (по префиксу из конфигурации)
- Показать пользователю предварительный обзор (кол-во слов, первое/последнее, частоты)
- Спросить, сколько топовых слов взять (N), подтвердить выбор
- Сгенерировать .apkg с карточками типа `anki.note_type_name` (по умолчанию: "Spanish note type").
  Поля: FrontText/FrontAudio/BackText/BackAudio/Image/Add Reverse. "Add Reverse" включено по умолчанию для обеих сторон.
  Тип и его ID определяются через AnkiConnect; при отсутствии или несовпадении полей — явная ошибка с подсказками.
- Сохранить пакет в безопасное место внутри `data/results/anki/` с временной меткой

Принципы безопасности и прозрачности:
- Всегда показывать пользователю, какой файл берётся, сколько будет карточек, примеры первой/последней строки
- Запрашивать подтверждение перед выполнением каждого важного шага

Историческая мотивация:
- В проекте уже есть 2 инструмента (скачивание HTML и текстовый анализ с экспортом в Excel)
- Этот инструмент закрывает сценарий «собрать колоду из топ-N новых слов» без вмешательства в живую коллекцию
"""

from __future__ import annotations

import sys
import time
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from tqdm import tqdm
except Exception:
    tqdm = None

# genanki используется для программной сборки .apkg
try:
    import genanki
except Exception as _e:  # Оставляем сообщение на этапе рантайма, чтобы пользователю было понятно
    genanki = None

# Доступ к конфигурации проекта и локальным helper'ам
sys.path.insert(0, str(Path(__file__).parents[1] / ".." / "src"))
sys.path.insert(0, str(Path(__file__).parent))
from spanish_analyser.config import config  # type: ignore
from spanish_analyser.components.anki_connector import AnkiConnector  # type: ignore

logger = logging.getLogger(__name__)
from openai_helper import generate_front_and_back, QuotaExceededError  # type: ignore


@dataclass
class PreviewRow:
    word: str
    count: int
    frequency: str


def _input_yes_no(prompt: str, default_no: bool = True) -> bool:
    """Запрашивает у пользователя подтверждение Y/N. По умолчанию — Нет.
    Возвращает True, если ответ 'y' или 'yes'."""
    suffix = "[y/N]" if default_no else "[Y/n]"
    ans = input(f"{prompt} {suffix} ").strip().lower()
    if not ans:
        return not default_no
    return ans in ("y", "yes", "д", "да")


def _find_latest_excel(results_dir: Path, filename_prefix: str) -> Optional[Path]:
    """Ищет последний по времени создания Excel-файл с указанным префиксом.

    Пояснение: отчёты текстового анализатора кладутся в `data/results` с префиксом
    (по умолчанию `driving_tests_analysis`). Берём последний файл для актуальности.
    
    Сначала пытаемся определить по имени файла (временная метка в имени),
    если не получается - по времени модификации файла.
    """
    if not results_dir.exists():
        return None
    candidates = [
        p for p in results_dir.glob("*.xlsx") if p.name.startswith(filename_prefix)
    ]
    if not candidates:
        return None
    
    # Пытаемся найти последний файл по временной метке в имени
    # Формат: prefix_YYYYMMDD_HHMMSS.xlsx
    try:
        def extract_timestamp(path: Path) -> str:
            # Убираем префикс и расширение, оставляем только временную метку
            name = path.stem  # без .xlsx
            if name.startswith(filename_prefix):
                timestamp_part = name[len(filename_prefix):]  # убираем префикс
                if timestamp_part.startswith('_'):
                    timestamp_part = timestamp_part[1:]  # убираем подчеркивание
                return timestamp_part
            return "00000000_000000"  # fallback для сортировки
        
        # Сортируем по временной метке в имени файла
        latest_by_name = max(candidates, key=lambda p: extract_timestamp(p))
        return latest_by_name
    except Exception:
        # Если что-то пошло не так с парсингом имени, используем время модификации
        return max(candidates, key=lambda p: p.stat().st_mtime)


def _load_words_from_excel(file_path: Path, sheet_name: Optional[str]) -> pd.DataFrame:
    """Читает Excel-таблицу и возвращает DataFrame с колонками: Word, Count, Frequency.

    Требования к формату соответствуют `WordAnalyzer.export_to_excel`.
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name or 0)
    required = {"Word", "Count", "Frequency"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Отсутствуют необходимые колонки в Excel: {', '.join(sorted(missing))}. "
            f"Файл: {file_path}"
        )
    # На всякий случай отсортируем по Count по убыванию (хотя сохранение уже в таком порядке)
    df = df.sort_values(by="Count", ascending=False).reset_index(drop=True)
    return df


def _preview_rows(df: pd.DataFrame, n: int) -> Tuple[PreviewRow, PreviewRow]:
    n = max(1, min(n, len(df)))
    first = df.iloc[0]
    last = df.iloc[n - 1]
    return (
        PreviewRow(word=str(first["Word"]), count=int(first["Count"]), frequency=str(first["Frequency"])),
        PreviewRow(word=str(last["Word"]), count=int(last["Count"]), frequency=str(last["Frequency"]))
    )


def _ensure_genanki_available():
    if genanki is None:
        raise RuntimeError(
            "Библиотека genanki не установлена. Добавьте 'genanki' в requirements и выполните установку."
        )


EXPECTED_FIELDS = [
    "FrontText",
    "FrontAudio",
    "BackText",
    "BackAudio",
    "Image",
    "Add Reverse",
]


def _resolve_model_or_fail(note_type_name: str):
    """Возвращает описание модели из живой коллекции через AnkiConnect.

    Возвращает кортеж: (model_id: int, fields: List[str], templates: List[dict], css: str)

    Требования и поведение (Fail Fast):
    - Anki с плагином AnkiConnect (2055492159) должен быть запущен
    - Модель с именем `note_type_name` должна существовать
    - Поля модели должны совпадать по именам и порядку с EXPECTED_FIELDS
    - Шаблоны и CSS используются ровно из существующей модели, чтобы избежать создания "note type+" при импорте
    При нарушении любого условия — понятная ошибка и завершение.
    """
    conn = AnkiConnector()
    if not conn.is_available():
        raise SystemExit(
            "AnkiConnect недоступен. Запустите Anki и убедитесь, что установлен и активен плагин 2055492159.\n"
            "Подсказки:\n"
            "  1) Откройте Anki → Инструменты → Add-ons → проверьте наличие AnkiConnect\n"
            "  2) Перезапустите Anki и повторите запуск генератора\n"
        )

    try:
        names_to_ids = conn.invoke('modelNamesAndIds') or {}
    except Exception as e:
        raise SystemExit(f"Не удалось получить список типов заметок через AnkiConnect: {e}")

    if note_type_name not in names_to_ids:
        available = ", ".join(sorted(names_to_ids.keys())) or "(пусто)"
        raise SystemExit(
            "Тип заметок не найден в Anki: '" + note_type_name + "'.\n"
            "Что можно сделать:\n"
            "  • Проверьте точное имя типа в Anki и поправьте anki.note_type_name в config.yaml\n"
            "  • Создайте в Anki тип заметок с полями: " + ", ".join(EXPECTED_FIELDS) + "\n"
            "  • Затем повторите запуск.\n"
            f"Доступные типы сейчас: {available}\n"
        )

    model_id = names_to_ids[note_type_name]
    # model_id может прийти как int или str — нормализуем
    try:
        model_id = int(model_id)
    except Exception:
        raise SystemExit(f"Некорректный ID модели для '{note_type_name}': {model_id}")

    # Валидация полей и их порядка
    try:
        fields = conn.invoke('modelFieldNames', {"modelName": note_type_name}) or []
    except Exception as e:
        raise SystemExit(f"Не удалось получить поля модели '{note_type_name}': {e}")

    if list(fields) != EXPECTED_FIELDS:
        raise SystemExit(
            "Поля типа заметок не совпадают с ожидаемыми.\n"
            f"Ожидается порядок: {', '.join(EXPECTED_FIELDS)}\n"
            f"В Anki сейчас:    {', '.join(fields)}\n"
            "Решения:\n"
            "  • Переименуйте/упорядочьте поля в Anki согласно ожидаемому списку\n"
            "  • Либо измените EXPECTED_FIELDS/данные экспорта (не рекомендуется)\n"
        )

    # Забираем шаблоны (в исходных именах и с тем же содержимым), и стили
    try:
        tmpls_raw = conn.invoke('modelTemplates', {"modelName": note_type_name}) or {}
        styling = conn.invoke('modelStyling', {"modelName": note_type_name}) or {}
    except Exception as e:
        raise SystemExit(f"Не удалось получить шаблоны/стили модели '{note_type_name}': {e}")

    # Преобразуем ответ modelTemplates в список шаблонов genanki.
    # Поддерживаем форматы: dict[name->tmpl], list[{name,qfmt,afmt,ord}], и
    # dict с values содержащими {qfmt,afmt,ord}.
    templates_list = []
    extracted: list[dict] = []
    if isinstance(tmpls_raw, list):
        extracted = [t for t in tmpls_raw if isinstance(t, dict)]
    elif isinstance(tmpls_raw, dict):
        # Значениями могут быть объекты шаблонов; иногда имена — ключи
        for name, t in tmpls_raw.items():
            if isinstance(t, dict):
                # Убедимся, что имя присутствует для надёжности
                t = {**t}
                t.setdefault('name', name)
                extracted.append(t)
    else:
        raise SystemExit(
            f"Неожиданный формат ответа modelTemplates для '{note_type_name}': {type(tmpls_raw)}"
        )

    # Сортируем по 'ord' если есть, иначе по имени, чтобы стабилизировать порядок
    extracted.sort(key=lambda t: (t.get('ord', 1_000_000), str(t.get('name', ''))))

    for t in extracted:
        tname = str(t.get('name', ''))
        qfmt = t.get('qfmt') or t.get('Front') or t.get('front')
        afmt = t.get('afmt') or t.get('Back') or t.get('back')
        if not tname or not isinstance(qfmt, str) or not isinstance(afmt, str):
            raise SystemExit(
                f"Шаблон '{tname or '<без имени>'}' модели '{note_type_name}' имеет неожиданную структуру. Проверьте в Anki."
            )
        templates_list.append({"name": tname, "qfmt": qfmt, "afmt": afmt})

    css = styling.get('css', '') if isinstance(styling, dict) else ''

    return model_id, list(fields), templates_list, css


def _build_model(note_type_name: str, model_id: int, fields: List[str], templates: List[dict], css: str) -> genanki.Model:
    """Создаёт тип заметки с нужными полями и реверсом (для упаковки в .apkg).

    Поля (в заданном порядке):
    1) FrontText
    2) FrontAudio
    3) BackText
    4) BackAudio
    5) Image
    6) Add Reverse (булево поле; непустое значение включает обратную карточку)

    Карточки:
    - Forward: показывает FrontText (+опционально аудио/картинку), на обороте BackText (+аудио)
    - Reverse: создаётся только если "Add Reverse" непустое; вопрос — BackText (+аудио), ответ — FrontText
    """
    return genanki.Model(
        model_id,
        note_type_name,
        fields=[{"name": f} for f in fields],
        templates=templates,
        css=css,
    )


def _build_deck_name(n: int) -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    return f"Spanish Staging::TopWords_{ts}_N{n}"


def _build_output_path(base_dir: Path, n: int) -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = base_dir / "anki"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"top_words_{ts}_N{n}.apkg"


def _make_deck_parallel(deck_name: str, top_df: pd.DataFrame, tags: List[str], model: genanki.Model) -> genanki.Deck:
    """Собирает deck и генерирует переводы через OpenAI параллельно с прогресс‑баром.

    - Переводы генерируются параллельно (ThreadPoolExecutor) с ограничением по конфигу
    - Прогресс отображается через tqdm (если установлен)
    - При ошибках процесс прерывается с понятным отчётом
    """
    deck_id = int(time.time())
    deck = genanki.Deck(deck_id, deck_name)

    # Подготовим задания: индексируем для сохранения исходного порядка
    tasks: list[tuple[int, str, str]] = []  # (idx, word, pos)
    df_reset = top_df.reset_index(drop=True)
    for idx, (_i, r) in enumerate(df_reset.iterrows()):
        word = str(r["Word"]).strip()
        pos_ru = str(r.get("Part of Speech", "неизвестно")).strip() if hasattr(r, 'get') else "неизвестно"
        tasks.append((idx, word, pos_ru))

    total = len(tasks)
    workers = config.get_ai_workers()
    print(f"⚙️ Параллельные запросы к ИИ: потоки={workers}")
    print(f"🔄 Генерация переводов: всего слов {total}")

    # Результаты по индексам; ошибки собираем для отчёта
    results: list[tuple[str, str] | None] = [None] * total
    errors: list[tuple[str, Exception]] = []

    # Прогресс-бар
    if tqdm:
        pbar = tqdm(
            total=total,
            desc="Генерация переводов (ИИ)",
            unit="слово",
            ncols=80,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}'
        )
    else:
        pbar = None

    def _job(w: str, pos: str):
        # FrontText — это значение из колонки Word (w), а в {{TERM}} отправляем только w без части речи
        # Базовая задержка для снижения нагрузки на API (из конфигурации)
        base_delay = config.get_ai_base_delay()
        time.sleep(base_delay)
        return generate_front_and_back(w, front_text=w, pos=pos)

    # Запускаем пул
    with ThreadPoolExecutor(max_workers=workers) as ex:
        future_to_idx: dict = {}
        for idx, w, pos in tasks:
            fut = ex.submit(_job, w, pos)
            future_to_idx[fut] = (idx, w)

        for fut in as_completed(future_to_idx):
            idx, w = future_to_idx[fut]
            try:
                front, back_html = fut.result()
                results[idx] = (front, back_html)
            except QuotaExceededError as e:
                # Специальная обработка ошибки квоты - сразу прерываем
                if pbar:
                    pbar.close()
                print(f"\n💰 {e}")
                print("\n🔧 Для решения проблемы:")
                print("   1. Откройте https://platform.openai.com/account/billing")
                print("   2. Пополните баланс или обновите план")
                print("   3. Повторите запуск после пополнения")
                raise SystemExit("Генерация прервана из-за исчерпания квоты OpenAI API.")
            except Exception as e:
                errors.append((w, e))
                # Логируем детали ошибки для диагностики
                logger.warning(f"Ошибка генерации для '{w}': {e}")
            finally:
                if pbar:
                    pbar.set_postfix({"ошибок": str(len(errors)), "потоки": str(workers)})
                    pbar.update(1)

    if pbar:
        pbar.close()

    # Если есть ошибки — выводим понятный отчёт и прерываемся
    if errors:
        print("❌ Ошибка генерации переводов для следующих слов:")
        for w, e in errors[:10]:
            print(f"   • {w}: {e}")
        if len(errors) > 10:
            print(f"   … и ещё {len(errors) - 10} шт.")
        raise SystemExit("Генерация прервана из‑за ошибок. Исправьте проблему и повторите.")

    # Добавляем заметки в исходном порядке
    for idx, (_i, r) in enumerate(df_reset.iterrows()):
        base_front = str(r["Word"]).strip()
        pair = results[idx]
        if not pair:
            raise SystemExit(f"Не удалось получить перевод для слова: {base_front}")
        front, back = pair

        fields = [
            front,  # FrontText
            "",     # FrontAudio
            back,   # BackText (HTML)
            "",     # BackAudio
            "",     # Image
            "True", # Add Reverse
        ]
        note = genanki.Note(model=model, fields=fields, tags=tags)
        deck.add_note(note)

    return deck

def _make_deck(deck_name: str, rows: List[PreviewRow], top_df: pd.DataFrame, n: int, tags: List[str], model: genanki.Model) -> genanki.Deck:
    """Собирает deck с заметками Basic. BackText — заглушка.

    Дополнительно:
    - Проставляем теги для облегчения фильтрации и истории импорта
    - GUID не фиксируем (генерирует genanki), чтобы не навредить существующим заметкам
    """
    deck_id = int(time.time())  # простой базовый ID; достаточно для уникальности во времени
    deck = genanki.Deck(deck_id, deck_name)

    # Обходим top_df построчно: Word, Count, Frequency
    for _, r in top_df.iterrows():
        base_front = str(r["Word"]).strip()
        back = "(перевод будет добавлен позже)"
        front = base_front

        # Всегда используем ИИ для генерации перевода
        try:
            # Если в Excel есть колонка 'Part of Speech', используем её, иначе — 'неизвестно'.
            pos_ru = str(r.get("Part of Speech", "неизвестно")).strip() if hasattr(r, 'get') else "неизвестно"
            print(f"🤖 Генерация перевода (ИИ) для: {base_front} [{pos_ru}] ...")
            if os.environ.get("SPANISH_ANALYSER_DEBUG") == "1":
                print(f"[DEBUG] Формируем запрос: слово='{base_front}', часть речи='{pos_ru}'")
            _front, back_html = generate_front_and_back(base_front, front_text=base_front, pos=pos_ru)
            front = _front
            back = back_html
        except QuotaExceededError as e:
            # Специальная обработка ошибки квоты
            print(f"\n💰 {e}")
            print("\n🔧 Для решения проблемы:")
            print("   1. Откройте https://platform.openai.com/account/billing")
            print("   2. Пополните баланс или обновите план")
            print("   3. Повторите запуск после пополнения")
            raise SystemExit("Генерация прервана из-за исчерпания квоты OpenAI API.")
        except Exception as e:
            # Прерываем процесс сборки с понятным сообщением — без тихих заглушек
            raise SystemExit(f"Ошибка генерации перевода для '{base_front}': {e}")

        # Формируем поля модели в нужном порядке. Аудио/картинка — пустые по умолчанию.
        # "Add Reverse" включаем по умолчанию, чтобы создать карточку в обе стороны.
        fields = [
            front,         # FrontText
            "",            # FrontAudio (например, [sound:file.mp3])
            back,          # BackText (HTML)
            "",            # BackAudio
            "",            # Image (например, <img src="..."> или имя файла)
            "True",        # Add Reverse (непустое = включено)
        ]

        note = genanki.Note(
            model=model,
            fields=fields,
            tags=tags,
        )
        deck.add_note(note)

    return deck


def run_cli() -> int:
    """Основной интерактивный сценарий CLI."""
    # 1) Проверяем зависимость genanki
    try:
        _ensure_genanki_available()
    except Exception as e:
        print(f"❌ {e}")
        return 1

    # 2) Получаем пути/настройки из конфигурации
    results_folder = Path(config.get_results_folder())
    filename_prefix = config.get_results_filename_prefix()
    sheet_name = config.get_main_sheet_name()

    print("📁 Папка результатов:", results_folder)
    print("🔎 Префикс отчётов:", filename_prefix)

    # ИИ должен использоваться всегда: проверяем наличие ключа заранее
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        print("❌ OPENAI_API_KEY не задан. Установите переменную окружения OPENAI_API_KEY для генерации перевода.")
        print("💡 Создайте файл .env с содержимым:")
        print("   OPENAI_API_KEY=your_api_key_here")
        return 1
    
    # Проверяем только наличие API ключа (без реальных запросов)
    print("🔌 API ключ OpenAI найден")
    print("💡 Проверка доступности будет выполнена при первом запросе")

    # 3) Определяем модель ИИ и показываем пользователю
    model_to_use = os.environ.get("OPENAI_MODEL") or config.get_ai_model()
    print("🧠 Модель ИИ:", model_to_use)

    # 4) Определяем тип заметок и его ID/шаблоны/стили в живой коллекции (через AnkiConnect)
    note_type_name = (config.get('anki.note_type_name') or "Spanish note type").strip()
    try:
        resolved_model_id, resolved_fields, resolved_templates, resolved_css = _resolve_model_or_fail(note_type_name)
    except SystemExit as e:
        print(f"❌ {e}")
        return 1

    print(f"🧩 Тип заметок: {note_type_name} (ID={resolved_model_id}) — поля и шаблоны подтверждены")

    # 5) Находим последний Excel-файл
    latest = _find_latest_excel(results_folder, filename_prefix)
    if latest is None:
        print("❌ Не найден ни один Excel-файл с результатами. Сначала запустите анализ текста и экспорт.")
        return 1

    print(f"📄 Найден последний файл: {latest.name}")
    if not _input_yes_no("Взять этот файл для генерации колоды?", default_no=False):
        manual = input("Укажите путь к Excel (.xlsx), или Enter для выхода: ").strip()
        if not manual:
            print("🚪 Отмена по запросу пользователя")
            return 0
        latest = Path(manual).expanduser().resolve()
        if not latest.exists():
            print(f"❌ Файл не найден: {latest}")
            return 1

    # 6) Читаем Excel и делаем предварительный просмотр
    try:
        df = _load_words_from_excel(latest, sheet_name)
    except Exception as e:
        print(f"❌ Ошибка чтения Excel: {e}")
        return 1

    total_rows = len(df)
    if total_rows == 0:
        print("⚠️ В таблице нет слов для экспорта")
        return 1

    print(f"📊 В таблице {total_rows} строк(и) с новыми словами")
    first_row = PreviewRow(str(df.iloc[0]["Word"]), int(df.iloc[0]["Count"]), str(df.iloc[0]["Frequency"]))
    last_row = PreviewRow(str(df.iloc[-1]["Word"]), int(df.iloc[-1]["Count"]), str(df.iloc[-1]["Frequency"]))
    print(f"   • Первое: {first_row.word} (Count={first_row.count}, Freq={first_row.frequency})")
    print(f"   • Последнее: {last_row.word} (Count={last_row.count}, Freq={last_row.frequency})")
    if not _input_yes_no("Всё верно?", default_no=False):
        print("🚪 Отмена по запросу пользователя")
        return 0

    # 7) Спросить N
    default_n = min(50, total_rows)
    raw_n = input(f"Сколько топовых слов взять? [по умолчанию {default_n}]: ").strip()
    n = default_n if not raw_n else max(1, min(int(raw_n), total_rows))

    # 8) Предпросмотр диапазона top-N
    top_df = df.head(n).copy()
    fprev, lprev = _preview_rows(top_df, n)
    print(f"🔝 Будут взяты {n} слов(а)")
    print(f"   • Первое: {fprev.word} (Count={fprev.count}, Freq={fprev.frequency})")
    print(f"   • Последнее: {lprev.word} (Count={lprev.count}, Freq={lprev.frequency})")
    if not _input_yes_no("Подтвердить выбор?", default_no=False):
        print("🚪 Отмена по запросу пользователя")
        return 0

    # 9) Имя колоды и путь сохранения
    default_deck_name = _build_deck_name(n)
    deck_name_in = input(f"Имя колоды? [Enter — {default_deck_name}]: ").strip()
    deck_name = deck_name_in or default_deck_name

    default_output = _build_output_path(results_folder, n)
    output_in = input(f"Путь для сохранения .apkg? [Enter — {default_output}]: ").strip()
    output_path = Path(output_in).expanduser() if output_in else default_output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("📦 Колода:", deck_name)
    print("💾 Файл:", output_path)
    print(f"🧩 Тип заметок: {note_type_name} (ID={resolved_model_id}, Add Reverse=on)")
    if not _input_yes_no("Приступить к сборке .apkg?", default_no=False):
        print("🚪 Отмена по запросу пользователя")
        return 0

    # 10) Сборка deck
    # Проставляем полезные теги: авто, размер, дата
    tags = [
        "auto",
        f"topN_{n}",
        time.strftime("date_%Y%m%d"),
    ]
    try:
        model = _build_model(note_type_name, resolved_model_id, resolved_fields, resolved_templates, resolved_css)
        deck = _make_deck_parallel(deck_name, top_df, tags, model)
        pkg = genanki.Package(deck)
        pkg.write_to_file(str(output_path))
    except Exception as e:
        print(f"❌ Ошибка при сборке .apkg: {e}")
        return 1

    print("✅ Готово! Файл сохранён:", output_path)
    print("ℹ️ Переводы для BackText сгенерированы с помощью ИИ.")
    return 0


def main():
    try:
        raise SystemExit(run_cli())
    except KeyboardInterrupt:
        print("\n🛑 Прервано пользователем")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
