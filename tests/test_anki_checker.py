import sys
from pathlib import Path
from unittest.mock import patch, Mock

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spanish_analyser.anki_checker import AnkiChecker


def test_is_anki_running_macos_false(monkeypatch):
    """
    На macOS-ветке эмулируем вывод ps aux без процессов Anki и пустой вывод pgrep.
    Ожидаем False.
    """
    checker = AnkiChecker()
    monkeypatch.setattr(checker, "system", "darwin")

    ps_completed = Mock()
    ps_completed.stdout = "root 1 0.0 0.1 /sbin/launchd\n"  # без Anki

    pgrep_completed = Mock()
    pgrep_completed.stdout = ""  # pgrep ничего не нашёл

    def _run_side_effect(args, capture_output=True, text=True, check=False, timeout=None):
        if args[:2] == ["ps", "aux"]:
            return ps_completed
        if args[:2] == ["pgrep", "-f"]:
            return pgrep_completed
        return ps_completed

    with patch("subprocess.run", side_effect=_run_side_effect):
        assert checker.is_anki_running() is False


def test_is_anki_running_macos_true(monkeypatch):
    """
    На macOS-ветке эмулируем вывод ps aux с процессом Anki.
    Ожидаем True.
    """
    checker = AnkiChecker()
    monkeypatch.setattr(checker, "system", "darwin")

    fake_completed = Mock()
    fake_completed.stdout = "user 123 0.0 0.1 /Applications/Anki.app/Contents/MacOS/Anki\n"

    with patch("subprocess.run", return_value=fake_completed):
        assert checker.is_anki_running() is True


def test_get_anki_processes_parsing(monkeypatch):
    """
    Проверяем парсинг строк `ps aux` в get_anki_processes() на macOS-ветке.
    """
    checker = AnkiChecker()
    monkeypatch.setattr(checker, "system", "darwin")

    # Сконструируем минимально валидную строку ps aux с достаточным числом полей
    # USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
    line = (
        "user 123 0.0 0.1 0 0 ?? S 10:00 0:00.00 /Applications/Anki.app/Contents/MacOS/Anki\n"
    )
    fake_completed = Mock()
    fake_completed.stdout = line

    with patch("subprocess.run", return_value=fake_completed):
        procs = checker.get_anki_processes()
        assert isinstance(procs, list)
        assert len(procs) == 1
        assert procs[0]["pid"] == "123"
        assert "Anki" in procs[0]["command"]
