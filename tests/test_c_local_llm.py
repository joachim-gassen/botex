import os 
import pytest

import botex

from tests.utils import *

from dotenv import load_dotenv
load_dotenv("secrets.env")

@pytest.mark.dependency(
        name="run_local_bots",
        scope='session',
        depends=[
            "botex_session",
            "botex_db"
        ]
)
def test_can_survey_be_completed_by_local_bots_with_botex_starting_llama_cpp_server():
    assert os.path.exists(os.environ.get("PATH_TO_LLAMA_SERVER")), "You are testing local bots with botex starting the llama server, therefore you need to provide the path to the llama server cli in the environment variable PATH_TO_LLAMA_SERVER."
    assert os.path.exists(os.environ.get("LOCAL_LLM_PATH")), "You are testing local bots with botex starting the llama server, therefore you need to provide the path to the local model in the environment variable LOCAL_LLM_PATH."
    delete_botex_db()
    otree_proc = start_otree()
    botex_session = init_otree_test_session()
    urls = botex.get_bot_urls(
        botex_session["session_id"], "tests/botex.db"
    )
    assert len(urls) == 2
    botex.run_bots_on_session(
        session_id=botex_session["session_id"],
        bot_urls=botex_session["bot_urls"],
        botex_db="tests/botex.db",
        model={"start_llama_server": True}
    )
    stop_otree(otree_proc)
    assert True

@pytest.mark.dependency(
        name="run_local_bots",
        scope='session',
        depends=[
            "botex_session",
            "botex_db"
        ]
)
def test_can_survey_be_completed_by_local_bots_already_running_llama_cpp_server():
    '''
    This test is to check if the bots can be run with a manually started llama server. It is important that the server is started on port 8081, so as not to interfere with the default port 8080 that llama.cpp server uses and is being utilized in the previous test. 
    '''
    delete_botex_db()
    otree_proc = start_otree()
    botex_session = init_otree_test_session()
    urls = botex.get_bot_urls(
        botex_session["session_id"], "tests/botex.db"
    )
    assert len(urls) == 2
    botex.run_bots_on_session(
        session_id=botex_session["session_id"],
        bot_urls=botex_session["bot_urls"],
        botex_db="tests/botex.db",
        model={"llama_server_url": "http://localhost:8081"}
    )
    stop_otree(otree_proc)
    assert True

@pytest.mark.dependency(
    name="conversations_db_local_bots", scope='session',
    depends=["run_local_bots"]
)
def test_can_conversation_data_be_obtained():
    conv = botex.read_conversations_from_botex_db(botex_db="tests/botex.db")
    assert isinstance(conv, list)
    assert len(conv) == 2

@pytest.mark.dependency(
    name="conversations_complete", scope='session',
    depends=["conversations_db_local_bots"]
)
def test_conversation_complete():
    check_conversation_and_export_answers('local')        
