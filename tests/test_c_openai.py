import csv
import json
from numbers import Number

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
def test_is_conversation_complete():
    def add_answer_and_reason(qtext, id_, a):
        for i,qst in enumerate(qtext):
            if qst['id'] == id_:
                qtext[i]['answer'] = a['answer']
                qtext[i]['reason'] = a['reason']
                break
    
    err_start = [
        'I am sorry', 'Unfortunately', 'Your response was not valid'
    ]
    convs = botex.read_conversations_from_botex_db(botex_db="tests/botex.db")
    with open("tests/questions.csv") as f:
        qtexts = list(csv.DictReader(f))
        qids = set([q['id'] for q in qtexts])
    
    answers = {}
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
                if 'answers' in r:
                    qs = r['answers']
                    assert isinstance(qs, dict)
                    for a in qs:
                        answers.update({a: qs[a]})
    ids = set()
    for id_, a in answers.items():
        assert isinstance(a, dict)
        assert isinstance(id_, str)
        assert isinstance(a['reason'], str)
        assert a['answer'] is not None
        ids = ids.union({id_})
        if id_ == "id_integer_field": 
            assert isinstance(a['answer'], str) or isinstance(a['answer'], int)
        elif id_ == "id_float_field":
            assert isinstance(a['answer'], str) or isinstance(a['answer'], Number)
        elif id_ == "id_boolean_field":
            assert isinstance(a['answer'], str) or isinstance(a['answer'], bool)
        elif id_ in [
            "id_string_field", "id_feedback",
            "id_choice_integer_field"
        ]:
            assert isinstance(a['answer'], str)
        add_answer_and_reason(qtexts, id_, a)
        
        
    assert ids == qids
    with open("tests/questions_and_answers_openai.csv", 'w') as f:
        writer = csv.DictWriter(f, fieldnames=qtexts[0].keys())
        writer.writeheader()
        writer.writerows(qtexts)
