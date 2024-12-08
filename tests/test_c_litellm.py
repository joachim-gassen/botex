import json
import os

import pytest
import botex

from tests.utils import *


from dotenv import load_dotenv
load_dotenv("secrets.env")

@pytest.mark.dependency(name="api_key", depends=["secrets"], scope='session')
def test_secret_contains_openai_key(model):
    global api_key 
    api_key = None
    provider = get_model_provider(model)
    if provider == "llamacpp" or provider == "ollama":
        assert True
        return
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
    
    assert api_key


@pytest.mark.dependency(
    name="run_bots", scope='session',
    depends=["participants_db", "api_key"]
)
def test_can_survey_be_completed_by_bots(model):
    otree_proc = start_otree()
    global botex_session
    botex_session = init_otree_test_session()
    urls = botex.get_bot_urls(
        botex_session["session_id"], "tests/botex.db"
    )
    assert len(urls) == 2
    botex.run_bots_on_session(
        model = model,
        api_key = api_key,
        session_id=botex_session["session_id"], 
        bot_urls=botex_session["bot_urls"],
        botex_db="tests/botex.db"
    )
    stop_otree(otree_proc)
    assert True

@pytest.mark.dependency(
    name="run_bots_full_host", scope='session',
    depends=["participants_db", "api_key"]
)
def test_can_survey_be_completed_by_bots_full_hist(model):
    vendor = get_model_provider(model)
    # Ollama chokes on full history
    if vendor == "llamacpp" or vendor == "ollama":
        return
    global botex_session
    otree_proc = start_otree()
    botex_session = init_otree_test_session(botex_db="tests/botex_full_hist.db")
    urls = botex.get_bot_urls(
        botex_session["session_id"], botex_db="tests/botex_full_hist.db",
    )
    assert len(urls) == 2
    botex.run_bots_on_session(
        model = model,
        api_key = api_key,
        session_id=botex_session["session_id"], 
        bot_urls=botex_session["bot_urls"],
        botex_db="tests/botex.db",
        full_conv_history=True
    )
    stop_otree(otree_proc)
    assert True

@pytest.mark.dependency(
    name="conversations_db", scope='session',
    depends=["run_bots"]
)
def test_can_conversation_data_be_obtained(model):
    conv = botex.read_conversations_from_botex_db(
        botex_db="tests/botex.db", session_id=botex_session["session_id"]
    )
    assert isinstance(conv, list)
    assert len(conv) == 2

@pytest.mark.dependency(
    name="conversations_db_open_ai_key_purged", scope='session',
    depends=["conversations_db"]
)
def test_is_open_ai_key_purged_from_db(model):
    conv = botex.read_conversations_from_botex_db(
        botex_db="tests/botex.db", session_id=botex_session["session_id"]
    )
    bot_parms = json.loads(conv[0]['bot_parms'])
    assert bot_parms['openai_api_key'] is None or bot_parms['openai_api_key'] == "******"
    assert bot_parms['api_key'] is None or bot_parms['api_key'] == "******"
    assert len(conv) == 2

@pytest.mark.dependency(
    name="conversations_complete", scope='session',
    depends=["conversations_db"]
)
def test_conversation_complete(model):
    check_conversation_and_export_answers(model, botex_session['session_id'])

