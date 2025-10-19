import importlib
from pathlib import Path
from unittest.mock import patch


def test_download_tests_module_imports_without_practicatest_auth_error():
    # Smoke check: module imports successfully (relative imports resolved)
    m = importlib.import_module('spanish_analyser.tools.web_scraper.download_tests')
    assert hasattr(m, 'download_available_tests')


def test_cli_run_web_scraper_uses_download_function_stub(monkeypatch):
    # Patch the download function to avoid network and heavy logic
    m = importlib.import_module('spanish_analyser.tools.web_scraper.download_tests')
    monkeypatch.setattr(m, 'download_available_tests', lambda: True, raising=True)

    cli = importlib.import_module('spanish_analyser.cli')
    assert cli.run_web_scraper() is True


def test_download_available_tests_happy_path_wo_network(tmp_path, monkeypatch):
    """Happy path без сети: эмулируем .env и внешние зависимости.

    ВАЖНО: не создаём/не удаляем реальный .env в репозитории.
    Вместо этого подменяем Path.exists в модуле download_tests для конкретного пути.
    """
    repo_root = Path(__file__).parent.parent
    env_file = repo_root / '.env'

    m = importlib.import_module('spanish_analyser.tools.web_scraper.download_tests')

    # Подменяем проверку .env внутри download_tests только для нужного пути
    orig_exists = m.Path.exists

    def _fake_exists(self):  # type: ignore[override]
        if str(self) == str(env_file):
            return True
        return orig_exists(self)

    monkeypatch.setattr(m.Path, 'exists', _fake_exists, raising=True)

    class FakeAuth:
        def __init__(self):
            self.session = object()
        def login(self):
            return True
        def close(self):
            pass

    # Table with only Premium/login buttons to avoid actual downloads
    FAKE_TABLE_HTML = """
    <table>
      <tr><th>Fecha</th><th>Estado</th><th>Col3</th><th>Col4</th><th>Acción</th></tr>
      <tr>
        <td>01-01-2024</td>
        <td>Libre</td>
        <td></td>
        <td></td>
        <td><button>LOGIN</button></td>
      </tr>
    </table>
    """

    class FakeParser:
        def __init__(self, session):
            self.session = session
        def get_tests_table(self):
            return FAKE_TABLE_HTML

    # Ensure downloads go into tmp path
    monkeypatch.setattr(m, 'PracticaTestAuth', FakeAuth, raising=True)
    monkeypatch.setattr(m, 'PracticaTestParser', FakeParser, raising=True)
    monkeypatch.setattr(m.config, 'get_downloads_folder', lambda: str(tmp_path), raising=False)

    assert m.download_available_tests() is True
