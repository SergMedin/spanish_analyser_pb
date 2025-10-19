import sys
from pathlib import Path
from unittest.mock import Mock

# Добавляем путь к src для доступа к модулям
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spanish_analyser.tools.web_scraper.test_downloader import TestDownloader as DownloaderUnderTest


def _session_ok_html(html: str):
    session = Mock()
    resp = Mock()
    resp.status_code = 200
    resp.text = html
    resp.content = html.encode("utf-8")
    session.get = Mock(return_value=resp)
    return session


def test_parse_tests_table_extracts_rows(tmp_path):
    html_table = """
    <table>
      <tr><th>Fecha</th><th>Estado</th><th>Col3</th><th>Col4</th><th>Acción</th></tr>
      <tr>
        <td>01-01-2024</td>
        <td>Libre</td>
        <td></td>
        <td></td>
        <td><a href="/tests/permiso-B/online">TEST &gt;</a></td>
      </tr>
      <tr>
        <td>02-01-2024</td>
        <td>Libre</td>
        <td></td>
        <td></td>
        <td><button>LOGIN</button></td>
      </tr>
    </table>
    """

    downloader = DownloaderUnderTest(_session_ok_html(""), downloads_path=str(tmp_path))
    rows = downloader.parse_tests_table(html_table)
    # Ожидаем 2 строки (кроме хедера)
    assert len(rows) == 2
    # Кнопка TEST должна распознаться
    assert any(r["button_type"] == "TEST" for r in rows)


def test_get_existing_downloads_detects_files(tmp_path):
    # Создаём файлы формата test_YYYY-MM-DD.html
    (tmp_path / "test_2024-01-01.html").write_text("<html>")
    (tmp_path / "test_2024-02-01.html").write_text("<html>")

    d = DownloaderUnderTest(_session_ok_html(""), downloads_path=str(tmp_path))
    dates = d.get_existing_downloads()
    assert set(dates) == {"2024-01-01", "2024-02-01"}


def test_get_downloadable_tests_filters_by_existing(tmp_path):
    d = DownloaderUnderTest(_session_ok_html(""), downloads_path=str(tmp_path))
    # Смоделируем, что один файл уже существует
    (tmp_path / "test_2024-01-01.html").write_text("<html>")

    tests_data = [
        {"date": "01-01-2024", "status": "Libre", "button_type": "TEST", "href": "/tests/permiso-B/online"},
        {"date": "02-01-2024", "status": "Libre", "button_type": "TEST", "href": "/tests/permiso-B/online"},
        {"date": "03-01-2024", "status": "Libre", "button_type": "Premium", "href": "/premium"},
    ]

    to_dl = d.get_downloadable_tests(tests_data)
    # Доступной должна остаться только 02-01-2024 с типом TEST
    dates = {t["download_date"] for t in to_dl}
    assert dates == {"2024-01-02"}
