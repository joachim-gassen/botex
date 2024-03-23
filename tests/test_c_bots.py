import pytest
import botex

from tests.utils import *

@pytest.mark.dependency(name="openai_key", depends=["secrets"], scope='session')
def test_secret_contains_openai_key():
    with open("secrets.env") as f:
        for line in f:
            if "OPENAI_API_KEY" in line:
                assert line.split("=")[1]

@pytest.mark.dependency(
    name="participants_db", scope='session',
    depends=["botex_db", "botex_session"]
)
def test_session_is_recorded_in_botex_db():
    delete_botex_db()
    otree_proc = start_otree()
    botex_session = init_otree_test_session()
    participants = botex.read_participants_from_botex_db(botex_db="tests/botex.db")
    assert isinstance(participants, list)
    assert len(participants) == 2
    p1 = participants[0]
    assert isinstance(p1, dict)
    assert isinstance(p1["participant_id"], str)
    assert p1["session_id"] == botex_session["session_id"]
    assert p1["is_human"] == 0
    assert isinstance(p1["url"], str)
    assert isinstance(p1["time_in"], str)
    assert p1["time_out"] == None
    stop_otree(otree_proc)
    delete_botex_db()

@pytest.mark.dependency(
    name="run_bots", scope='session',
    depends=["botex_session", "openai_key"]
)
def test_can_survey_be_completed_by_bots():
    otree_proc = start_otree()
    botex_session = init_otree_test_session()
    urls = botex.get_bot_urls(
        botex_session["session_id"], "tests/botex.db"
    )
    assert len(urls) == 2
    botex.run_bots_on_session(
        session_id=botex_session["session_id"], 
        bot_urls=botex_session["bot_urls"],
        botex_db="tests/botex.db"
    )
    stop_otree(otree_proc)
    assert True

@pytest.mark.dependency(
    name="conversations_db", scope='session',
    depends=["run_bots"]
)
def test_can_conversation_data_be_obtained():
    conv = botex.read_conversations_from_botex_db(botex_db="tests/botex.db")
    assert isinstance(conv, list)
    assert len(conv) == 2

