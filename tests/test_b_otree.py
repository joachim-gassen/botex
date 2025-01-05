import os
import time

import pytest

import botex

from tests.utils import *

@pytest.mark.dependency(name="botex_env", scope='session')
def test_botex_env_exists_in_project_root():
    assert os.path.exists("botex.env")

@pytest.mark.dependency(
    name="otree_project_path", scope='session', depends=["botex_env"]
)
def test_botex_env_has_otree_project_path():
    botex.load_botex_env()
    assert os.getenv("OTREE_PROJECT_PATH")

@pytest.mark.dependency(name="otree_starts", depends=["otree_project_path"])
def test_does_otree_start():
    botex.load_botex_env()
    otree_proc = botex.start_otree_server()
    otree_running = otree_proc.poll() is None
    assert otree_running
    if otree_running: botex.stop_otree_server(otree_proc)

@pytest.mark.dependency(name="botex_session", scope='session', depends=["otree_starts"])
def test_can_otree_session_be_initialized():
    botex.load_botex_env()
    otree_proc = botex.start_otree_server()
    botex_session = init_otree_test_session()
    botex.stop_otree_server(otree_proc)
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
    otree_proc = botex.start_otree_server()
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
    botex.stop_otree_server(otree_proc)
    delete_botex_db()


if __name__ == "__main__":
    test_does_otree_start()

