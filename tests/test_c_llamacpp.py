import os 
import pytest

import botex

from tests.utils import *

from dotenv import load_dotenv
load_dotenv("secrets.env")

@pytest.mark.dependency(name="llama_server_executable", scope='session')
@pytest.mark.skipif(
    not eval(os.environ.get("START_LLAMA_SERVER")),
    reason="Using externally started llama.cpp server"
)
def test_llama_server_executable_exists():
    assert os.path.exists(os.environ.get("PATH_TO_LLAMA_SERVER"))

@pytest.mark.dependency(name="local_llm_path", scope='session')
@pytest.mark.skipif(
    not eval(os.environ.get("START_LLAMA_SERVER")),
    reason="Using externally started llama.cpp server"
)
def test_local_llm_path_exists():
    assert os.path.exists(os.environ.get("LOCAL_LLM_PATH")) 

@pytest.mark.dependency(
        name="run_local_bots",
        scope='session',
        depends=[
            "botex_session",
            "botex_db"
        ]
)
def test_can_survey_be_completed_by_local_bots():
    delete_botex_db()
    otree_proc = start_otree()
    global botex_session
    botex_session = init_otree_test_session()
    urls = botex.get_bot_urls(
        botex_session["session_id"], "tests/botex.db"
    )
    assert len(urls) == 2
    botex.run_bots_on_session(
        session_id=botex_session["session_id"],
        bot_urls=botex_session["bot_urls"],
        botex_db="tests/botex.db",
        model="local"
    )
    stop_otree(otree_proc)
    assert True

@pytest.mark.dependency(
    name="conversations_db_local_bots", scope='session',
    depends=["run_local_bots"]
)
def test_can_conversation_data_be_obtained():
    conv = botex.read_conversations_from_botex_db(
        botex_db="tests/botex.db", session_id=botex_session["session_id"]
    )
    assert isinstance(conv, list)
    assert len(conv) == 2

@pytest.mark.dependency(
    name="conversations_complete", scope='session',
    depends=["conversations_db_local_bots"]
)
def test_conversation_complete():
    check_conversation_and_export_answers('llamacpp', botex_session['session_id'])        
