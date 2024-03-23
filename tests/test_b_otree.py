import subprocess
import os
import dotenv
import time
import pytest

import psutil
import botex

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
    assert len(botex_session) == 3
    assert isinstance(botex_session["session_id"], str)
    assert isinstance(botex_session["human_urls"], list)
    assert len(botex_session["human_urls"]) == 0
    assert isinstance(botex_session["bot_urls"], list)
    assert len(botex_session["bot_urls"]) == 2
