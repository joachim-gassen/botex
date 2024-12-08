import os
import dotenv
import time

import pytest

from tests.utils import *

@pytest.mark.dependency(name="secrets", scope='session')
def test_secret_exists_in_project_root():
    assert os.path.exists("secrets.env")

@pytest.mark.dependency(name="otree_admin", scope='session', depends=["secrets"])
def test_secret_has_otree_admin_password():
    with open("secrets.env") as f:
        for line in f:
            if "OTREE_ADMIN_PASSWORD" in line:
                assert line.split("=")[1]

@pytest.mark.dependency(name="otree_rest_key", scope='session', depends=["secrets"])
def test_secret_has_otree_rest_key():
    with open("secrets.env") as f:
        for line in f:
            if "OTREE_REST_KEY" in line:
                assert line.split("=")[1]

@pytest.mark.dependency(name="otree_starts")
def test_does_otree_start():
    otree_proc = start_otree()
    time.sleep(OTREE_STARTUP_WAIT)
    otree_running = otree_proc.poll() is None
    if otree_running: stop_otree(otree_proc)

@pytest.mark.dependency(name="botex_session", scope='session', depends=["otree_starts"])
def test_can_otree_session_be_initialized():
    dotenv.load_dotenv("secrets.env")
    otree_proc = start_otree()
    time.sleep(OTREE_STARTUP_WAIT)
    botex_session = init_otree_test_session()
    stop_otree(otree_proc)
    delete_botex_db()
    assert len(botex_session) == 5
    assert isinstance(botex_session["session_id"], str)
    assert isinstance(botex_session["participant_code"], list)
    assert len(botex_session["participant_code"]) == 2
    assert isinstance(botex_session["is_human"], list)
    assert botex_session["is_human"] == [False, False]
    assert isinstance(botex_session["human_urls"], list)
    assert len(botex_session["human_urls"]) == 0
    assert isinstance(botex_session["bot_urls"], list)
    assert len(botex_session["bot_urls"]) == 2

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

