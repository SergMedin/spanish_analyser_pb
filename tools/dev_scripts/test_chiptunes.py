#!/usr/bin/env python3
"""
Тестовый скрипт для проверки новых 8-битных мелодий в чиптюн-плеере.

Использование:
    python test_chiptunes.py [имя_пресета]

Доступные пресеты:
- nokia_classic (новый Nokia рингтон)
- tetris_theme (мелодия Тетриса)
- mario_theme (Super Mario Bros)
- simple_mobile (простая мобильная мелодия)
- boomer_mobile (алиас для simple_mobile)
- cambio_groove (оригинальный)
- neo_pulse (оригинальный)
- ambient_chips (оригинальный)
"""

import sys
import time
from pathlib import Path

# Добавляем путь к основному модулю
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from spanish_analyser.tools.chiptune_player import ChiptunePlayer, PRESETS
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("💡 Убедитесь, что вы запускаете скрипт из правильной директории")
    sys.exit(1)


def main():
    """Основная функция для тестирования чиптюн-мелодий."""
    
    # Определяем пресет из аргументов командной строки
    preset_name = sys.argv[1] if len(sys.argv) > 1 else "nokia_classic"
    
    if preset_name not in PRESETS:
        print(f"❌ Неизвестный пресет: {preset_name}")
        print(f"📋 Доступные пресеты: {', '.join(PRESETS.keys())}")
        sys.exit(1)
    
    print(f"🎵 Тестируем мелодию: {preset_name}")
    print(f"📝 Длина паттерна: {len(PRESETS[preset_name])} нот")
    
    # Показываем первые несколько нот для справки
    notes = PRESETS[preset_name][:16]
    print(f"🎼 Первые 16 нот: {notes}")
    
    # Создаем и запускаем плеер
    player = ChiptunePlayer()
    
    # Устанавливаем пресет через переменную окружения (симулируем)
    import os
    os.environ["SPANISH_ANALYSER_CHIPTUNE_PRESET"] = preset_name
    os.environ["SPANISH_ANALYSER_CHIPTUNE_TEMPO"] = "0.15"  # медленнее для лучшего восприятия
    os.environ["SPANISH_ANALYSER_CHIPTUNE_AMP"] = "0.2"     # тише
    
    print("🔄 Запускаем плеер...")
    
    if player.start():
        print(f"✅ Плеер запущен! Играет мелодия '{preset_name}'")
        print("⏹️  Нажмите Ctrl+C для остановки")
        
        try:
            # Играем 30 секунд
            for i in range(30):
                time.sleep(1)
                print(f"⏱️  {i+1}/30 сек", end="\r")
        except KeyboardInterrupt:
            print("\n🛑 Остановка по требованию пользователя")
        
        print("\n🔇 Останавливаем плеер...")
        player.stop()
        print("✅ Плеер остановлен")
        
    else:
        print("❌ Не удалось запустить плеер")
        print("💡 Возможные причины:")
        print("   - Отсутствуют библиотеки numpy/sounddevice")
        print("   - Нет доступного аудиоустройства")
        print("   - Проблемы с драйверами звука")


if __name__ == "__main__":
    main()
