from tempfile import NamedTemporaryFile

import pytest
import botex

from tests.utils import *


@pytest.mark.dependency(name="botex_db", scope="session")
def test_botex_db():
    temp_file = NamedTemporaryFile().name
    db_manager = botex.DatabaseManager(temp_file)
    participant_table = db_manager.execute_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='participants'",
        fetch=True,
    )
    assert participant_table, "Participants table not created"
    conversation_table = db_manager.execute_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'",
        fetch=True,
    )
    assert conversation_table, "Conversations table not created"
    db_manager.close()
    delete_botex_db(temp_file)
