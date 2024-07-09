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
    def add_answer_and_reason(qtext, q):
        for i,qst in enumerate(qtext):
            if qst['id'] == q['id']:
                qtext[i]['answer'] = q['answer']
                qtext[i]['reason'] = q['reason']
                break
    
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
        for m in conv:
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
    with open("tests/questions_and_answers_openai.csv", 'w') as f:
        writer = csv.DictWriter(f, fieldnames=qtexts[0].keys())
        writer.writeheader()
        writer.writerows(qtexts)
