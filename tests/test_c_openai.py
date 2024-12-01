import json

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
    assert p1["time_in"] == None
    assert p1["time_out"] == None
    stop_otree(otree_proc)
    delete_botex_db()

@pytest.mark.dependency(
    name="run_bots", scope='session',
    depends=["participants_db", "openai_key"]
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
    name="run_bots_full_host", scope='session',
    depends=["participants_db", "openai_key"]
)
def test_can_survey_be_completed_by_bots_full_hist():
    otree_proc = start_otree()
    botex_session = init_otree_test_session(botex_db="tests/botex_full_hist.db")
    urls = botex.get_bot_urls(
        botex_session["session_id"], botex_db="tests/botex_full_hist.db",
    )
    assert len(urls) == 2
    botex.run_bots_on_session(
        session_id=botex_session["session_id"], 
        bot_urls=botex_session["bot_urls"],
        botex_db="tests/botex_full_hist.db",
        full_conv_history=True
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

@pytest.mark.dependency(
    name="conversations_db_open_ai_key_purged", scope='session',
    depends=["conversations_db"]
)
def test_is_open_ai_key_purged_from_db():
    conv = botex.read_conversations_from_botex_db(botex_db="tests/botex.db")
    bot_parms = json.loads(conv[0]['bot_parms'])
    assert bot_parms['openai_api_key'] is None or bot_parms['openai_api_key'] == "******"
    assert len(conv) == 2

@pytest.mark.dependency(
    name="conversations_complete", scope='session',
    depends=["conversations_db"]
)
def test_conversation_complete():
    check_conversation_and_export_answers('openai')   
