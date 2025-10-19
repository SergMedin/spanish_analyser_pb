#!/usr/bin/env python3
"""
Интерфейс командной строки для Spanish Analyser

Этот модуль предоставляет единый CLI для всех инструментов проекта:
1. Web Scraper - загрузка HTML страниц с practicatest.com
2. Text Analyzer - анализ текста и создание Excel отчётов
3. Anki Deck Generator - создание колод Anki
"""

import os
import sys
import argparse
from typing import Optional
from pathlib import Path

# Используем пакетные импорты вместо манипуляций с sys.path


def run_web_scraper():
    """Запускает веб-скрапер для загрузки тестов"""
    print("🌐 Запуск веб-скрапера...")
    
    try:
        from spanish_analyser.tools.web_scraper.download_tests import download_available_tests
        success = download_available_tests()
        
        if success:
            print("✅ Веб-скрапер завершил работу успешно")
            return True
        else:
            print("❌ Веб-скрапер завершил работу с ошибками")
            return False
            
    except ImportError as e:
        print(f"❌ Ошибка импорта модуля веб-скрапера: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при запуске веб-скрапера: {e}")
        return False


def run_text_analyzer():
    """Запускает текстовый анализатор"""
    print("📊 Запуск текстового анализатора...")
    
    try:
        from spanish_analyser.tools.text_analyzer.driving_tests_analyzer import DrivingTestsAnalyzer
        
        # Создаём анализатор (пути берутся из config.yaml)
        analyzer = DrivingTestsAnalyzer()
        
        try:
            # Подключаемся к Anki
            print("🔗 Подключение к Anki...")
            if not analyzer.connect_to_anki():
                print("⚠️ Продолжаю без Anki...")
            
            # Анализируем HTML файлы
            print("\n📄 Начинаю анализ HTML файлов...")
            analysis_result = analyzer.analyze_html_files()
            
            print(f"\n📊 Результаты анализа:")
            print(f"   Обработано файлов: {analysis_result['files_processed']}")
            print(f"   Найдено слов: {analysis_result['words_found']}")
            print(f"   Уникальных слов: {analysis_result['unique_words']}")
            
            # Экспортируем результаты
            print(f"\n📁 Экспортирую результаты...")
            export_file = analyzer.export_results()
            
            if export_file:
                print(f"✅ Результаты экспортированы в: {export_file}")
            
            
            # Показываем статистику кэша
            try:
                from .cache import CacheManager
                cache = CacheManager.get_cache()
                cache_stats = cache.stats_dict()
                if cache_stats['hits'] > 0 or cache_stats['stores'] > 0:
                    print(f"\n💾 Статистика кэша:")
                    print(f"   Попаданий: {cache_stats['hits']}")
                    print(f"   Промахов: {cache_stats['misses']}")
                    print(f"   Файлов в кэше: {cache_stats['files']}")
                    print(f"   Размер кэша: {cache_stats['size_mb']:.1f} МБ")
            except Exception:
                pass
            
            return True
            
        finally:
            analyzer.close()
            
    except ImportError as e:
        print(f"❌ Ошибка импорта модуля текстового анализатора: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при запуске текстового анализатора: {e}")
        return False


def run_anki_deck_generator():
    """Запускает генератор Anki колод"""
    print("🧩 Запуск Anki Deck Generator...")
    
    try:
        from spanish_analyser.tools.anki_deck_generator.anki_deck_maker import run_cli as run_anki_deck_maker
        
        code = run_anki_deck_maker()
        if code == 0:
            print("✅ Anki Deck Generator завершил работу успешно")
            return True
        else:
            print("❌ Anki Deck Generator завершил работу с ошибками")
            return False
            
    except ImportError as e:
        print(f"❌ Ошибка импорта модуля Anki Deck Generator: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при запуске Anki Deck Generator: {e}")
        return False


def _apply_music_env_from_config(cfg) -> None:
    """Устанавливает ENV по значениям из config.yaml, если не заданы явно."""
    os.environ.setdefault("SPANISH_ANALYSER_CHIPTUNE_PRESET", str(cfg.get_chiptune_preset()))
    os.environ.setdefault("SPANISH_ANALYSER_CHIPTUNE_TEMPO", str(cfg.get_chiptune_tempo()))
    os.environ.setdefault("SPANISH_ANALYSER_CHIPTUNE_DURATION", str(cfg.get_chiptune_duration()))
    os.environ.setdefault("SPANISH_ANALYSER_CHIPTUNE_AMP", str(cfg.get_chiptune_amp()))
    audio_dev = cfg.get_audio_device()
    if audio_dev is not None:
        os.environ.setdefault("SPANISH_ANALYSER_AUDIO_DEVICE", str(audio_dev))


def _start_chiptune(cfg) -> Optional["ChiptunePlayer"]:  # type: ignore[name-defined]
    """Пробует запустить чиптюн и вернуть плеер. При ошибке — None."""
    try:
        sys.path.insert(0, str(Path(__file__).parent / "tools"))
        from chiptune_player import ChiptunePlayer  # type: ignore
        _apply_music_env_from_config(cfg)
        player = ChiptunePlayer()
        if not player.start():
            print("🎵 Чиптюн: аудио недоступно (пропускаю)")
            return None
        preset = os.environ.get("SPANISH_ANALYSER_CHIPTUNE_PRESET", "cambio_groove")
        tempo = os.environ.get("SPANISH_ANALYSER_CHIPTUNE_TEMPO", "0.11")
        duration = os.environ.get("SPANISH_ANALYSER_CHIPTUNE_DURATION", "150")
        print(f"🎵 Чиптюн: запущен (preset={preset}, tempo={tempo}s, duration≈{duration}s)")
        return player
    except Exception:
        print("🎵 Чиптюн: не удалось инициализировать (пропускаю)")
        return None


def _stop_chiptune(player: Optional["ChiptunePlayer"]) -> None:  # type: ignore[name-defined]
    try:
        if player is not None and getattr(player, "is_running", False):
            player.stop()
    except Exception:
        pass


def main():
    """Основная функция CLI"""
    # Инициализируем логирование из конфигурации в самом начале
    from .config import config
    
    # Специальная обработка SPANISH_ANALYSER_DEBUG для переопределения уровня логирования
    if os.environ.get('SPANISH_ANALYSER_DEBUG') == '1':
        # Устанавливаем DEBUG уровень принудительно
        os.environ['SPANISH_ANALYSER_LOGGING__LEVEL'] = 'DEBUG'
        # Перезагружаем конфигурацию чтобы применились ENV переопределения
        config._apply_env_overrides()
        # Отладочная информация
        print(f"🔍 DEBUG режим активирован через SPANISH_ANALYSER_DEBUG=1")
        print(f"🔍 Уровень логирования из config: {config.get_logging_level()}")
    
    # Применяем конфигурацию логирования (с возможной переинициализацией после ENV-override)
    config._configure_logging_if_needed(force=True)
    # Ранняя инициализация кэша: создаёт подпапки и мигрирует старые файлы из корня cache/.
    try:
        from .cache import CacheManager
        CacheManager.get_cache()
    except Exception:
        pass
    # Явно сообщаем текущий эффективный уровень логирования (для диагностики)
    import logging as _logging
    _eff = _logging.getLevelName(_logging.getLogger().getEffectiveLevel())
    print(f"🪵 Логирование активно на уровне: {_eff} (config={config.get_logging_level()})")
    
    parser = argparse.ArgumentParser(
        description="Spanish Analyser - Анализ испанских текстов с интеграцией Anki",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python -m spanish_analyser.cli --scraper          # Запуск только веб-скрапера
  python -m spanish_analyser.cli --analyzer         # Запуск только текстового анализатора
  python -m spanish_analyser.cli --anki-generator   # Запуск генератора Anki колод
  python -m spanish_analyser.cli --all              # Запуск всех инструментов
  python -m spanish_analyser.cli                    # Интерактивный режим
        """
    )
    
    parser.add_argument(
        '--scraper', 
        action='store_true',
        help='Запустить веб-скрапер для загрузки тестов'
    )
    
    parser.add_argument(
        '--analyzer', 
        action='store_true',
        help='Запустить текстовый анализатор'
    )
    
    parser.add_argument(
        '--anki-generator', 
        action='store_true',
        help='Запустить генератор Anki колод'
    )
    
    parser.add_argument(
        '--all', 
        action='store_true',
        help='Запустить все инструменты'
    )
    
    args = parser.parse_args()
    
    print("🚗 Spanish Analyser - Анализ испанских текстов")
    print("=" * 50)
    
    if args.all:
        print("🔄 Запуск всех инструментов...")
        success = True
        success &= run_web_scraper()
        print("\n" + "=" * 50)
        success &= run_text_analyzer()
        print("\n" + "=" * 50)
        success &= run_anki_deck_generator()
        
        if success:
            print("\n✅ Все инструменты завершили работу успешно")
        else:
            print("\n❌ Некоторые инструменты завершились с ошибками")
        
    elif args.scraper:
        run_web_scraper()
        
    elif args.analyzer:
        run_text_analyzer()
        
    elif args.anki_generator:
        run_anki_deck_generator()
        
    else:
        # Интерактивный режим
        from .config import config
        
        use_music = config.is_chiptune_enabled() or (os.environ.get("SPANISH_ANALYSER_CHIPTUNE", "0") == "1")
        player: Optional["ChiptunePlayer"] = None  # type: ignore[name-defined]
        
        while True:
            # Запускаем музыку только в главном меню
            if use_music and (player is None or not getattr(player, "is_running", False)):
                player = _start_chiptune(config)

            print("\n📋 Доступные инструменты:")
            print("1. 🌐 Web Scraper - загрузка тестов с practicatest.com")
            print("2. 📊 Text Analyzer - анализ текста и создание отчётов")
            print("3. 🧩 Anki Deck Generator - создание колод Anki")
            print("4. 🚪 Выход")
            if use_music:
                print("\n🎵 Фоновая 8-бит музыка активна в главном меню")

            choice = input("\nВыберите инструмент (1-4): ").strip()

            if choice == '1':
                _stop_chiptune(player)
                player = None
                run_web_scraper()
            elif choice == '2':
                _stop_chiptune(player)
                player = None
                run_text_analyzer()
            elif choice == '3':
                # По требованию: в третьем инструменте музыка продолжает играть
                run_anki_deck_generator()
            elif choice == '4':
                _stop_chiptune(player)
                print("👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор. Попробуйте снова.")


if __name__ == "__main__":
    main()
