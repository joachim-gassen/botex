import csv
import json
from numbers import Number
import os 
import pytest

import botex

from tests.utils import start_otree, stop_otree, init_otree_test_session, delete_botex_db

with open("secrets.env") as f:
    cfg = {}
    for line in f:
        if not line.strip() or line.startswith("#"):
            continue
        key, value = line.strip().split("=")
        cfg[key] = value

user_prompts = {
    "system": "You are participating in an online survey and/or experiment. Please fully assume this role and answer everything from the first person point of view. Each prompt contains a summary of the survey/experiment including your answers so far, scraped text data from a webpage continuing the survey/experiment, and detailed tasks for you on how to analyze this text data. The materials might contain information on how participants are being compensated or paid for their participation. If this is the case, please act as if this compensation also applies to you and make sure to include this information in the summary. Answers must be given as JSON code ONLY. No text outside of the JSON answer is allowed at any time. In each prompt, I will provide you with detailed information on the respective format."
}

@pytest.mark.dependency(name="llama_server_executable", scope='session')
def test_llama_server_executable_exists():
    assert os.path.exists(cfg["path_to_compiled_llama_server_executable"])

@pytest.mark.dependency(name="local_model_path", scope='session')
def test_local_model_path_exists():
    assert os.path.exists(cfg["local_model_path"])


@pytest.mark.dependency(name="num_layers_to_offload_to_gpu", scope='session')
def test_number_of_layers_to_offload_to_gpu():
    if cfg.get("number_of_layers_to_offload_to_gpu"):
        assert isinstance(int(cfg["number_of_layers_to_offload_to_gpu"]), int)
        # TODO: a more specific test to see if there is a gpu to offload to


@pytest.mark.dependency(
        name="run_local_bots",
        scope='session',
        depends=[
            "llama_server_executable",
            "local_model_path",
            "num_layers_to_offload_to_gpu",
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
        model="local",
        local_model_cfg=cfg,
        user_prompts=user_prompts
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
    with open("tests/questions_and_answers_local.csv", 'w') as f:
        writer = csv.DictWriter(f, fieldnames=qtexts[0].keys())
        writer.writeheader()
        writer.writerows(qtexts)
