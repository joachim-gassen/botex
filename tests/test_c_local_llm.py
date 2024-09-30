import csv
import json
from numbers import Number
import os 
import pytest

import botex

from tests.utils import start_otree, stop_otree, init_otree_test_session, delete_botex_db

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
    conv = botex.read_conversations_from_botex_db(botex_db="tests/botex.db")
    assert isinstance(conv, list)
    assert len(conv) == 2

@pytest.mark.dependency(
    name="conversations_complete", scope='session',
    depends=["conversations_db_local_bots"]
)
        
def test_is_conversation_complete():
    def add_answer_and_reason(qtext, q):
        for i,qst in enumerate(qtext):
            if qst['id'] == q['id']:
                qtext[i]['answer'] = q['answer']
                qtext[i]['reason'] = q['reason']
                break
    
    err_start = [
        'I am sorry', 'Unfortunately', 'Your response was not valid'
    ]
    convs = botex.read_conversations_from_botex_db(botex_db="tests/botex.db")
    with open("tests/questions.csv") as f:
        qtexts = list(csv.DictReader(f))
        qids = set([q['id'] for q in qtexts])
    
    questions = []
    for c in convs:
        assert isinstance(c['id'], str)
        assert isinstance(c['bot_parms'], str) 
        assert isinstance(c['conversation'], str)
        bot_parms = json.loads(c['bot_parms'])
        assert isinstance(bot_parms, dict)
        conv = json.loads(c['conversation'])
        assert isinstance(conv, list)
        for i, m in enumerate(conv):
            if i+2 < len(conv) and conv[i+1]['role'] == 'user':
                    if any(conv[i + 1]['content'].startswith(prefix) for prefix in err_start):
                        continue
            assert isinstance(m, dict)
            assert isinstance(m['role'], str)
            assert isinstance(m['content'], str)
            if m['role'] == 'assistant':
                try:
                    r = m['content']
                    start = r.find('{', 0)
                    end = r.rfind('}', start)
                    r = r[start:end+1]
                    r = json.loads(r, strict=False)
                except:
                    break
                if 'questions' in r:
                    qs = r['questions']
                    assert isinstance(qs, list)
                    for q in qs: questions.append(q)    
    ids = set()
    for q in questions:
        assert isinstance(q, dict)
        assert isinstance(q['id'], str)
        assert isinstance(q['reason'], str)
        assert q['answer'] is not None
        ids = ids.union({q['id']})
        if q['id'] == "id_integer_field": 
            assert isinstance(q['answer'], str) or isinstance(q['answer'], int)
        elif q['id'] == "id_float_field":
            assert isinstance(q['answer'], str) or isinstance(q['answer'], Number)
        elif q['id'] == "id_boolean_field":
            assert isinstance(q['answer'], str) or isinstance(q['answer'], bool)
        elif q['id'] in [
            "id_string_field", "id_feedback",
            "id_choice_integer_field"
        ]:
            assert isinstance(q['answer'], str)
        add_answer_and_reason(qtexts, q)
        
    assert ids == qids
    with open("tests/questions_and_answers_local.csv", 'w') as f:
        writer = csv.DictWriter(f, fieldnames=qtexts[0].keys())
        writer.writeheader()
        writer.writerows(qtexts)
