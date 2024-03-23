from tempfile import NamedTemporaryFile
import pytest
import botex 

from tests.utils import *

@pytest.mark.dependency(name="botex_db", scope='session')
def test_botex_db():
    temp_file = NamedTemporaryFile().name
    conn = botex.setup_botex_db(temp_file)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='participants'"
    )
    table_exists = cursor.fetchone()
    assert table_exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'"
    )
    table_exists = cursor.fetchone()
    assert table_exists
    cursor.close()
    conn.close()
    delete_botex_db(temp_file)
