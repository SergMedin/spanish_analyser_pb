import sys
from pathlib import Path
from unittest.mock import Mock

# Добавляем путь к src для доступа к модулям
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "spanish_analyser" / "tools" / "web_scraper"))

from practicatest_parser import PracticaTestParser


def _make_session_with_html(html: str):
    """Возвращает мок requests.Session, который на GET отдаёт заданный html."""
    session = Mock()
    response = Mock()
    response.status_code = 200
    response.content = html.encode("utf-8")
    response.text = html

    def _get(url, timeout=30):
        return response

    session.get = Mock(side_effect=_get)
    return session


def test_find_test_section():
    html = """
    <html>
      <body>
        <h2>Test del Permiso B con explicaciones</h2>
      </body>
    </html>
    """
    parser = PracticaTestParser(_make_session_with_html(html))
    section = parser.find_test_section()
    assert section is not None
    assert "Permiso B" in section.get_text()


def test_find_ver_los_test_button_button_and_link():
    html = """
    <html>
      <body>
        <button data-bs-target="#testsModal">VER LOS TEST</button>
        <div id="testsModal"><div class="modal-body">contenido</div></div>
      </body>
    </html>
    """
    parser = PracticaTestParser(_make_session_with_html(html))
    btn = parser.find_ver_los_test_button()
    assert btn is not None
    assert btn.name in ("button", "a")

    # Вариант с ссылкой
    html2 = """
    <html>
      <body>
        <a href="/tests/permiso-B">VER LOS TEST</a>
      </body>
    </html>
    """
    parser2 = PracticaTestParser(_make_session_with_html(html2))
    btn2 = parser2.find_ver_los_test_button()
    assert btn2 is not None
    assert btn2.name in ("button", "a")


def test_click_ver_los_test_modal_resolution():
    html = """
    <html>
      <body>
        <button data-bs-target="#testsModal">VER LOS TEST</button>
        <div id="testsModal"><table><tr><th>hdr</th></tr><tr><td>row</td></tr></table></div>
      </body>
    </html>
    """
    parser = PracticaTestParser(_make_session_with_html(html))
    assert parser.click_ver_los_test() is True
    # После клика modal должен быть установлен
    assert parser.current_modal is not None


def test_get_tests_table_and_parse():
    html = """
    <html>
      <body>
        <button data-bs-target="#testsModal">VER LOS TEST</button>
        <div id="testsModal">
          <table>
            <tr><th>Fecha</th><th>Estado</th><th>Acción</th></tr>
            <tr><td>01-01-2024</td><td>Libre</td><td>TEST</td></tr>
            <tr><td>05-01-2024</td><td>Libre</td><td>TEST</td></tr>
          </table>
        </div>
      </body>
    </html>
    """
    parser = PracticaTestParser(_make_session_with_html(html))
    table = parser.get_tests_table()
    assert table is not None

    data = parser.parse_tests_data()
    # Ожидаем минимум 2 записей
    assert isinstance(data, list) and len(data) >= 2



