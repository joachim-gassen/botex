import os
import csv
import json
from numbers import Number

import botex

OTREE_STARTUP_WAIT = 3

def delete_botex_db(botex_db = "tests/botex.db"):
    try:
        os.remove(botex_db)
    except OSError:
        pass

def delete_otree_db():
    try:
        os.remove("tests/otree/db.sqlite3")
    except OSError:
        pass    

def init_otree_test_session(botex_db = "tests/botex.db"):
    botex_session = botex.init_otree_session(
        config_name="botex_test", npart=2, botex_db = botex_db, 
    )
    return botex_session

def export_otree_data(csv_file):
    botex.export_otree_data(csv_file)
    assert os.path.exists(csv_file)
    try:
        with open(csv_file) as f:
            participants = list(csv.DictReader(f))
    except:
        assert False
    assert len(participants) == 2
    for p in participants:
        assert p['participant._current_page_name'] == 'Thanks'

def get_model_provider(model):
    if "llamacpp" in model:
        return "llamacpp"
    if '/' in model:
        return model.split('/')[0]
    return "openai"

def create_answer_message(model):
    if model == "llamacpp":
        type = model
    else:
        type = get_model_provider(model)
    csv_file = f"tests/questions_and_answers_{type}.csv"
    if not os.path.exists(csv_file):
        return ""
    with open(csv_file) as f:
        quest_answers = list(csv.DictReader(f))
    am = ""
    for qa in quest_answers:
        am += (
            f"Question: '{qa['question']}'\n" +  
            f"Answer: '{qa['answer']}'\n" + 
            f"Rationale: '{qa['reason']}'\n\n"
        )
    return am[:-1]

def check_conversation_and_export_answers(model, session_id):
    type = get_model_provider(model)
    def add_answer_and_reason(qtext, id_, a):
        for i,qst in enumerate(qtext):
            if qst['id'] == id_ and 'answer' not in qst.keys():
                qtext[i]['answer'] = a['answer']
                qtext[i]['reason'] = a['reason']
                break
    
    err_start = [
        'I am sorry', 'Unfortunately', 'Your response was not valid'
    ]
    convs = botex.read_conversations_from_botex_db(
        botex_db="tests/botex.db", session_id=session_id
    )
    with open("tests/questions.csv") as f:
        qtexts = list(csv.DictReader(f))
        qids = [q['id'] for q in qtexts]
    
    answers = []
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
                        answers.append({a: qs[a]})
    ids = []
    for a in answers:
        id_ = list(a.keys())[0]
        a = a[id_]
        assert isinstance(a, dict)
        assert isinstance(id_, str)
        assert isinstance(a['reason'], str)
        assert a['answer'] is not None
        ids.append(id_)
        if id_ == "id_integer_field": 
            assert isinstance(a['answer'], str) or isinstance(a['answer'], int)
        elif id_ == "id_float_field":
            assert isinstance(a['answer'], str) or isinstance(a['answer'], Number)
        elif id_ == "id_boolean_field":
            assert isinstance(a['answer'], str) or isinstance(a['answer'], bool)
        elif id_ in [
            "id_string_field", "id_feedback",
            "id_choice_integer_field", "id_button_radio"
        ]:
            assert isinstance(a['answer'], str)
        add_answer_and_reason(qtexts, id_, a)

    assert len(ids) == len(qids)    
    assert set(ids) == set(qids)
    with open(f"tests/questions_and_answers_{type}.csv", 'w') as f:
        writer = csv.DictWriter(f, fieldnames=qtexts[0].keys())
        writer.writeheader()
        writer.writerows(qtexts)


    

