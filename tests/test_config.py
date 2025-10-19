import os
import tempfile
import textwrap
import sys
from pathlib import Path

# В тестах явно добавляем путь к src, чтобы импортировать пакет
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spanish_analyser.config import Config


def test_config_defaults_when_missing_file(tmp_path):
    """
    Проверяет, что при отсутствии файла конфигурации подставляются дефолтные значения.
    Этот тест важен, чтобы приложение было устойчивым к отсутствию config.yaml при запуске отдельных модулей.
    """
    # Создаём временную директорию без config.yaml и делаем её текущей
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        cfg = Config()
        # Проверяем несколько ключей из разных секций
        assert cfg.get("text_analysis.min_word_length") == 3
        assert cfg.get("excel.main_sheet_name") == "Word Analysis"
        # Пути по умолчанию должны указывать в data/..
        assert cfg.get_downloads_folder() == "data/downloads"
        assert cfg.get_results_folder() == "data/results"
    finally:
        os.chdir(cwd)


def test_config_overrides_from_yaml(tmp_path):
    """
    Проверяет, что значения из YAML перекрывают дефолты Config._get_default_config().
    Это гарантирует способность централизованно управлять поведением через config.yaml.
    """
    yaml_text = textwrap.dedent(
        """
        text_analysis:
          min_word_length: 5
        excel:
          main_sheet_name: "Custom Sheet"
        files:
          downloads_folder: "data/downloads"  # намеренно оставляем прежний путь
          results_folder: "data/results"
        """
    ).strip()

    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml_text, encoding="utf-8")

    cfg = Config(config_path=str(cfg_path))

    # Проверяем, что переопределения применились
    assert cfg.get_min_word_length() == 5
    assert cfg.get_main_sheet_name() == "Custom Sheet"
    # Неизменённые значения остаются дефолтными там, где YAML не задаёт
    assert cfg.get_web_scraper_timeout() == 30


def test_config_env_loading(tmp_path, monkeypatch):
    """
    Проверяет загрузку переменных окружения через load_dotenv().
    Мы эмулируем .env, устанавливая переменные окружения через monkeypatch,
    чтобы не зависеть от реального файла .env пользователя.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("PRACTICATEST_EMAIL", "user@example.com")
    monkeypatch.setenv("PRACTICATEST_PASSWORD", "secret")

    cfg = Config(config_path=str(tmp_path / "nonexistent.yaml"))

    assert cfg.get_env("OPENAI_API_KEY") == "sk-test-123"
    assert cfg.get_env("PRACTICATEST_EMAIL") == "user@example.com"
    assert cfg.get_env("PRACTICATEST_PASSWORD") == "secret"



