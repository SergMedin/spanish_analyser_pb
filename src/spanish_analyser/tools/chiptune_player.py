#!/usr/bin/env python3
"""
Простой чиптюн-плеер для фоновой 8-битной музыки во время работы CLI.

Назначение модуля:
- Включать ненавязчивую «8-битную» музыку при запуске интерактивной утилиты `make cli`.
- Работать безопасно: если нет зависимостей/аудиоустройства, просто ничего не делать и не мешать основной работе.

Как это устроено:
- Реализован синтез простых квадратных волн, напоминающих 8-битный звук, плюс короткий шум для «ударных».
- Воспроизведение происходит через `sounddevice.OutputStream` с колбэком, не блокируя основной поток.
- Предусмотрены методы `start()` и `stop()` для управления жизненным циклом плеера.

Зависимости:
- numpy
- sounddevice

Примечания по безопасности:
- Любые ошибки инициализации/воспроизведения перехватываются, модуль тихо отключается, чтобы не ломать CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, List, Callable
import math
import os

# Фолбэк-импорты: если нет зависимостей, модуль остаётся «пустым» и не мешает работе
try:
    import numpy as np  # type: ignore
    import sounddevice as sd  # type: ignore
except Exception:  # pragma: no cover - сознательно тихий фолбэк
    np = None  # type: ignore
    sd = None  # type: ignore


def libraries_available() -> bool:
    """Проверяет, доступны ли обязательные библиотеки для аудио.

    Возвращает True, только если и numpy, и sounddevice импортированы успешно.
    """
    return (np is not None) and (sd is not None)


class ChipSynth:
    """Простейший синтезатор квадратной волны + короткий шум.

    Идея: максимально лёгкий синтезатор в духе 8-бит. Реализована базовая арпеджио-петля,
    чтобы музыка играла «фоном» и не утомляла. Длительность и паттерн можно менять на лету.
    """

    def __init__(self, sample_rate: int = 44100) -> None:
        if np is None:
            raise RuntimeError("numpy недоступен, синтез невозможен")

        self.sample_rate = sample_rate
        self.phase: float = 0.0
        # Дефолтный темп: немного быстрее для поп-латин вайба
        self.note_length_seconds: float = 0.11
        self.note_length_samples: int = int(self.sample_rate * self.note_length_seconds)
        # По умолчанию используем пресет "cambio_groove" (см. PRESETS ниже)
        self.pattern = PRESETS.get("cambio_groove", [72, 76, 79, 84, 76, 79, 0, 72, 67, 71, 74, 79, 71, 74, 0, 67])
        self.pattern_index: int = 0
        self.current_frequency: float = (
            self.midi_to_freq(self.pattern[self.pattern_index])
            if self.pattern[self.pattern_index] > 0
            else 0.0
        )
        self.samples_left_in_note: int = self.note_length_samples
        self.noise_seed: int = 1
        self.amplitude: float = 0.15  # нейтральная громкость по умолчанию

    @staticmethod
    def midi_to_freq(midi_note: int) -> float:
        return 440.0 * (2 ** ((midi_note - 69) / 12))

    def set_tempo(self, note_length_seconds: float) -> None:
        """Изменить длительность ноты (темп) во время проигрывания."""
        self.note_length_seconds = max(0.04, float(note_length_seconds))
        self.note_length_samples = int(self.sample_rate * self.note_length_seconds)

    def set_pattern(self, midi_notes: list[int]) -> None:
        """Задать новый паттерн проигрывания (список MIDI-нот, 0 = пауза)."""
        if not midi_notes:
            return
        self.pattern = midi_notes
        self.pattern_index = 0
        m = self.pattern[self.pattern_index]
        self.current_frequency = self.midi_to_freq(m) if m > 0 else 0.0
        self.samples_left_in_note = self.note_length_samples

    def next_block(self, frames: int):
        """Синтезировать блок из `frames` сэмплов (моно)."""
        assert np is not None
        output = np.zeros(frames, dtype=np.float32)
        for i in range(frames):
            if self.samples_left_in_note <= 0:
                self.pattern_index = (self.pattern_index + 1) % len(self.pattern)
                midi_note = self.pattern[self.pattern_index]
                self.current_frequency = self.midi_to_freq(midi_note) if midi_note > 0 else 0.0
                self.samples_left_in_note = self.note_length_samples

            sample = 0.0
            if self.current_frequency > 0.0:
                # квадратная волна
                self.phase += self.current_frequency / self.sample_rate
                if self.phase >= 1.0:
                    self.phase -= 1.0
                square = 1.0 if self.phase < 0.5 else -1.0

                # простая огибающая для уменьшения щелчков
                position_in_note = self.note_length_samples - self.samples_left_in_note
                attack_samples = int(0.005 * self.sample_rate)  # 5 мс
                decay_samples = int(0.040 * self.sample_rate)   # 40 мс
                attack_gain = min(position_in_note / max(attack_samples, 1), 1.0)
                decay_gain = min(self.samples_left_in_note / max(decay_samples, 1), 1.0)
                envelope = min(attack_gain, decay_gain)

                sample += square * envelope * self.amplitude

            # короткий шум в начале каждой 8-й ноты для ритма
            if (self.pattern_index % 8 == 0) and (
                self.samples_left_in_note > self.note_length_samples - int(0.02 * self.sample_rate)
            ):
                self.noise_seed = (1103515245 * self.noise_seed + 12345) & 0x7FFFFFFF
                noise_value = ((self.noise_seed >> 16) / 32768.0 - 1.0) * 0.25
                fade = self.samples_left_in_note / max(self.note_length_samples, 1)
                sample += noise_value * fade

            output[i] = sample
            self.samples_left_in_note -= 1

        return output


def _build_presets() -> Dict[str, List[int]]:
    """Коллекция готовых паттернов (MIDI-ноты, 0 = пауза).

    - cambio_groove: в духе Cambio Dolor, прогрессия D–Bm–G–A, 64 шага
    - neo_pulse: в духе Matrix, минорный драйв Am–C–G–Em, 64 шага
    - ambient_chips: спокойный фон Am–F–C–G, 64 шага
    - nokia_classic: классический Nokia рингтон (Gran Vals), 48 шагов
    - tetris_theme: легендарная мелодия Тетриса (Korobeiniki), 64 шага
    - mario_theme: Super Mario Bros главная тема, 64 шага
    - simple_mobile: простая мобильная мелодия в стиле 2000-х, 64 шага
    - final_countdown: Europe - "The Final Countdown" в 8-битном стиле, 80 шагов
    - boomer_mobile: алиас для simple_mobile (совместимость)
    """
    cambio_groove = [
        # D
        62, 66, 69, 74, 66, 69, 74, 0, 62, 66, 69, 74, 66, 69, 74, 0,
        # Bm
        59, 62, 66, 71, 62, 66, 71, 0, 59, 62, 66, 71, 62, 66, 71, 0,
        # G
        67, 71, 74, 79, 71, 74, 79, 0, 67, 71, 74, 79, 71, 74, 79, 0,
        # A
        69, 73, 76, 81, 73, 76, 81, 0, 69, 73, 76, 81, 73, 76, 81, 0,
    ]

    neo_pulse = [
        # Am
        69, 72, 76, 81, 72, 76, 81, 0, 69, 72, 76, 81, 72, 76, 81, 0,
        # C
        72, 76, 79, 84, 76, 79, 84, 0, 72, 76, 79, 84, 76, 79, 84, 0,
        # G
        67, 71, 74, 79, 71, 74, 79, 0, 67, 71, 74, 79, 71, 74, 79, 0,
        # Em
        64, 67, 71, 76, 67, 71, 76, 0, 64, 67, 71, 76, 67, 71, 76, 0,
    ]

    ambient_chips = [
        # Am
        69, 0, 72, 0, 76, 0, 81, 0, 72, 0, 76, 0, 81, 0, 72, 0,
        # F
        65, 0, 69, 0, 72, 0, 77, 0, 69, 0, 72, 0, 77, 0, 72, 0,
        # C
        72, 0, 76, 0, 79, 0, 84, 0, 76, 0, 79, 0, 84, 0, 79, 0,
        # G
        67, 0, 71, 0, 74, 0, 79, 0, 71, 0, 74, 0, 79, 0, 74, 0,
    ]

    # Классический Nokia рингтон (Gran Vals) в 8-битном стиле
    # Тональность: E major, характерная последовательность
    nokia_classic = [
        # Основная мелодия (8 тактов по 8 нот)
        76, 72, 78, 81, 85, 83, 74, 76,  # E D F# G# C# B D E
        76, 72, 78, 81, 85, 83, 74, 76,  # повтор
        76, 72, 78, 81, 85, 83, 74, 76,  # повтор
        76, 72, 78, 81, 85, 83, 74, 76,  # повтор
        # Вариация с паузами для 8-битного звучания
        76, 0, 72, 0, 78, 0, 81, 0, 85, 0, 83, 0, 74, 0, 76, 0,
        76, 0, 72, 0, 78, 0, 81, 0, 85, 0, 83, 0, 74, 0, 76, 0,
    ]

    # Легендарная мелодия Тетриса (Korobeiniki) в Em
    tetris_theme = [
        # Основная тема А (2 такта)
        76, 71, 72, 74, 72, 71, 69, 69, 72, 76, 74, 72, 71, 71, 72, 74,
        # Продолжение темы А
        76, 72, 69, 69, 0, 0, 0, 0, 74, 77, 81, 79, 77, 76, 72, 76,
        # Тема B (более высокие ноты)
        74, 72, 71, 71, 72, 74, 76, 72, 69, 69, 0, 0, 0, 0, 0, 0,
        # Повтор с вариацией
        76, 71, 72, 74, 72, 71, 69, 69, 72, 76, 74, 72, 71, 71, 72, 74,
    ]

    # Super Mario Bros главная тема в C major
    mario_theme = [
        # Знаменитое начало "ta-da-da-da-dum, da-dum"
        76, 76, 0, 76, 0, 72, 76, 0, 79, 0, 0, 0, 67, 0, 0, 0,
        # Продолжение мелодии
        72, 0, 0, 67, 0, 0, 64, 0, 0, 69, 0, 71, 0, 70, 69, 0,
        # Вариация
        67, 76, 79, 81, 77, 79, 0, 76, 72, 74, 71, 0, 0, 0, 0, 0,
        # Повтор начала
        72, 0, 0, 67, 0, 0, 64, 0, 0, 69, 0, 71, 0, 70, 69, 0,
    ]

    # Простая 8‑битная мелодия в духе старых мобильных рингтонов
    # Тональность: C major, простая и запоминающаяся
    simple_mobile = [
        # Простой мотив
        72, 76, 79, 84, 79, 76, 72, 0, 74, 77, 81, 86, 81, 77, 74, 0,
        69, 72, 76, 81, 76, 72, 69, 0, 67, 71, 74, 79, 74, 71, 67, 0,
        # Повтор с вариацией
        72, 76, 79, 84, 79, 76, 72, 0, 74, 77, 81, 86, 81, 77, 74, 0,
        72, 0, 76, 0, 79, 0, 84, 0, 79, 0, 76, 0, 72, 0, 0, 0,
    ]

    # Europe - "The Final Countdown" в 8-битном стиле
    # Тональность: D minor, знаменитая мелодия с характерными паузами
    final_countdown = [
        # Знаменитое начало "We're leaving together..."
        # D C Bb A G F Eb D (в октаве 4)
        74, 72, 70, 69, 67, 65, 63, 62,  # Основная тема
        74, 72, 70, 69, 67, 65, 63, 62,  # повтор
        74, 72, 70, 69, 67, 65, 63, 62,  # повтор
        74, 72, 70, 69, 67, 65, 63, 62,  # повтор
        # Вариация с паузами для 8-битного звучания
        74, 0, 72, 0, 70, 0, 69, 0, 67, 0, 65, 0, 63, 0, 62, 0,
        74, 0, 72, 0, 70, 0, 69, 0, 67, 0, 65, 0, 63, 0, 62, 0,
        # Более высокие ноты для кульминации
        86, 84, 82, 81, 79, 77, 75, 74,  # октава выше
        86, 84, 82, 81, 79, 77, 75, 74,  # повтор
        86, 0, 84, 0, 82, 0, 81, 0, 79, 0, 77, 0, 75, 0, 74, 0,
    ]

    return {
        "cambio_groove": cambio_groove,
        "neo_pulse": neo_pulse,
        "ambient_chips": ambient_chips,
        "nokia_classic": nokia_classic,
        "tetris_theme": tetris_theme,
        "mario_theme": mario_theme,
        "simple_mobile": simple_mobile,
        "final_countdown": final_countdown,
        # Оставляем старое название для совместимости
        "boomer_mobile": simple_mobile,
    }


# Глобальная таблица пресетов доступна сразу после загрузки модуля
PRESETS: Dict[str, List[int]] = _build_presets()


def generate_matrix_neon_pattern(target_duration_seconds: float, note_length_seconds: float) -> List[int]:
    """Генерирует длинный паттерн (≈2–3 минуты) в духе «Матрицы».

    Идея:
    - Ключ Em. Прогрессия по кругу: Em → C → G → D (тёмно-героический вайб)
    - Стиль: пульсирующее арпеджио с паузами, периодические вариации (октава/проходящие ноты)
    - 1 такт = 16 шагов. Длительность такта = 16 * note_length_seconds
    - Кол-во тактов рассчитывается из целевой длительности.
    """
    # Определения трезвучий (в 4–5 октавах), MIDI-ноты
    Em = [64, 67, 71, 76]   # E4, G4, B4, E5
    C  = [60, 64, 67, 72]   # C4, E4, G4, C5
    G  = [67, 71, 74, 79]   # G4, B4, D5, G5
    D  = [62, 66, 69, 74]   # D4, F#4, A4, D5

    progression = [Em, C, G, D]

    # Шаблоны арпеджио на 1 такт (16 шагов)
    def arp_bar(chord: List[int], variant: int) -> List[int]:
        root, third, fifth, octave = chord
        if variant % 4 == 0:
            # Базовый пульс
            return [root, fifth, third, octave, fifth, third, 0, 0,
                    root, fifth, third, octave, fifth, third, 0, 0]
        elif variant % 4 == 1:
            # Октававверх на акцентах
            return [octave, fifth, third, root, fifth, third, 0, 0,
                    octave, fifth, third, root, fifth, third, 0, 0]
        elif variant % 4 == 2:
            # Вариант с удвоенным корнем
            return [root, root, fifth, third, octave, fifth, 0, 0,
                    root, root, fifth, third, octave, fifth, 0, 0]
        else:
            # Хроматический сосед (на последнем блоке для напряжения)
            chroma = root - 1 if root in (64, 76) else third - 1
            return [root, fifth, third, octave, fifth, third, 0, 0,
                    root, fifth, third, octave, fifth, chroma, 0, 0]

    bar_seconds = 16.0 * max(0.04, float(note_length_seconds))
    num_bars = max(8, int(math.ceil(max(30.0, float(target_duration_seconds)) / bar_seconds)))

    pattern: List[int] = []
    for i in range(num_bars):
        chord = progression[i % len(progression)]
        # Раз в 8 тактов поднимаем октаву корня для «прорыва»
        variant = i % 8
        bar = arp_bar(chord, variant)
        pattern.extend(bar)

    return pattern


# Карта генераторов длинных паттернов
PRESET_GENERATORS: Dict[str, Callable[[float, float], List[int]]] = {
    "matrix_neon": generate_matrix_neon_pattern,
}


@dataclass
class ChiptunePlayer:
    """Управляет жизненным циклом аудио-потока чиптюн-музыки.

    Использование:
        player = ChiptunePlayer()
        player.start()
        ... работа CLI ...
        player.stop()
    """

    sample_rate: int = 44100
    channels: int = 1
    _stream: Optional["sd.OutputStream"] = None  # type: ignore[name-defined]
    _synth: Optional[ChipSynth] = None
    _enabled: bool = False
    _device: Optional[int | str] = None

    def start(self) -> bool:
        """Пытается запустить музыку. Возвращает True при успехе, иначе False.

        Любые ошибки проглатываются (логика CLI при этом не страдает).
        """
        if not libraries_available():
            return False
        if self._enabled:
            return True
        try:
            self._synth = ChipSynth(sample_rate=self.sample_rate)

            # Настраиваем пресет/темп/громкость из переменных окружения
            preset_name = os.environ.get("SPANISH_ANALYSER_CHIPTUNE_PRESET", "cambio_groove")
            tempo_env = os.environ.get("SPANISH_ANALYSER_CHIPTUNE_TEMPO")
            amp_env = os.environ.get("SPANISH_ANALYSER_CHIPTUNE_AMP")
            duration_env = os.environ.get("SPANISH_ANALYSER_CHIPTUNE_DURATION", "150")

            # Применяем пресет
            # Если пресет процедурный — генерируем длинный паттерн на заданную длительность
            gen = PRESET_GENERATORS.get(preset_name)
            if gen is not None:
                try:
                    target_s = float(duration_env)
                except Exception:
                    target_s = 150.0
                # Учитываем темп, если задан заранее
                if tempo_env:
                    try:
                        self._synth.set_tempo(float(tempo_env))
                    except Exception:
                        pass
                pattern = gen(target_s, self._synth.note_length_seconds)
                self._synth.set_pattern(pattern)
            else:
                preset = PRESETS.get(preset_name)
                if preset:
                    self._synth.set_pattern(preset)
            # Темп (длительность ноты)
            if tempo_env:
                try:
                    self._synth.set_tempo(float(tempo_env))
                except Exception:
                    pass
            # Громкость
            if amp_env:
                try:
                    self._synth.amplitude = max(0.01, min(0.5, float(amp_env)))
                except Exception:
                    pass

            def _callback(outdata, frames, time_info, status):  # type: ignore[no-redef]
                # В случае предупреждений от драйвера просто продолжаем работу
                block = self._synth.next_block(frames) if self._synth else None
                if block is None:
                    outdata.fill(0)
                    return
                outdata[:, 0] = block  # моно

            # Позволяем выбирать устройство через переменную окружения SPANISH_ANALYSER_AUDIO_DEVICE
            # Значение может быть индексом устройства (int) или именем (str)
            device_env = None
            try:
                device_env = os.environ.get("SPANISH_ANALYSER_AUDIO_DEVICE")
                if device_env is not None:
                    # попытаемся привести к int, если это индекс
                    try:
                        self._device = int(device_env)
                    except ValueError:
                        self._device = device_env
            except Exception:
                self._device = None

            self._stream = sd.OutputStream(
                channels=self.channels,
                samplerate=self.sample_rate,
                callback=_callback,
                device=self._device,
            )
            self._stream.start()
            self._enabled = True
            return True
        except Exception:
            # Тихо отключаемся, если аудио недоступно/ошибка драйвера и т.п.
            self._stream = None
            self._synth = None
            self._enabled = False
            return False

    def stop(self) -> None:
        """Останавливает музыку, если она была запущена."""
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        finally:
            self._stream = None
            self._synth = None
            self._enabled = False

    @property
    def is_running(self) -> bool:
        return self._enabled

