import csv
import json
import sqlite3
import logging
from os import environ


def retrieve_responses(resp_str):
    try:
        resp_str = resp_str
        start = resp_str.find('{', 0)
        end = resp_str.rfind('}', start)
        resp_str = resp_str[start:end+1]
        cont = json.loads(resp_str, strict = False)
        if 'answers' in cont: return cont['answers']
    except:
        logging.info(
            f"message :'{resp_str}' failed to load as json"
        )
        return None
        
def parse_history(h):
    c = json.loads(h, strict = False)
    answers = []
    pot_a = None
    for m in c:
        if m['role'] == 'assistant':
            pot_a = retrieve_responses(m['content'])
        else: 
            if pot_a is not None:
                if m['content'][:7] == 'Perfect': answers.append(pot_a)
                pot_a = None

    ids = []
    round = 1

    for i,a in enumerate(answers):
        for id_, a in a.items():
            ids.append(id_)
            c_id = ids.count(id_)
            if c_id > 1:
                if c_id > round:
                    round = c_id
        answers[i]['round'] = round
    return answers
    
def parse_conversation(c):
    return {
        'participant_id':  c['id'],
        'session_id': json.loads(c['bot_parms'])['session_id'],
        'answers': parse_history(c['conversation'])
    }

def read_participants_from_botex_db(session_id = None, botex_db = None):
    """
    Read the participants table from the botex database.

    Parameters:
        session_id (str, optional): A session ID to filter the results.
        botex_db (str, optional): The name of a SQLite database file.
        If not provided, it will try to read the file name from
        the environment variable BOTEX_DB.

    Returns:
        List of Dicts: A list of dictionaries with participant data.
    """

    if botex_db is None: botex_db = environ.get('BOTEX_DB')
    conn = sqlite3.connect(botex_db)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    if session_id:
        cursor.execute(
            "SELECT * FROM participants WHERE session_id = ?", (session_id,)
        )
    else:
        cursor.execute("SELECT * FROM participants")
    sessions = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return sessions


def read_conversations_from_botex_db(
        participant_id = None, botex_db = None
    ):
    """
    Reads the conversations table from the botex database. 
    The conversation table contains the messages exchanged 
    with the LLM underlying the bot.

    Parameters:
        participant_id (str, optional): A Participant ID to filter the results.
        botex_db (str, optional): The name of a SQLite database file.
            If not provided, it will try to read the file name from
            the environment variable BOTEX_DB.
        
    Returns:
        List of dicts: A list of dictionaries with the conversation data.
    """
    if botex_db is None: botex_db = environ.get('BOTEX_DB')
    conn = sqlite3.connect(botex_db)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    if participant_id:
        cursor.execute(
            "SELECT * FROM conversations WHERE id = ?", (participant_id,)
        )
    else:
        cursor.execute("SELECT * FROM conversations")
    conversations = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return conversations

# We might want to implement a session id filter at some point
def read_responses_from_botex_db(botex_db = None):
    """
    Extracts the responses and their rationales from the botex conversation data. 

    Parameters:
        botex_db (str, optional): The name of a SQLite database file.
            If not provided, it will try to read the file name from
            the environment variable BOTEX_DB.

    Returns:
        List of dicts: A list of dictionaries with the rationale data.
    """
    
    cs = read_conversations_from_botex_db(botex_db = botex_db)
    resp = [parse_conversation(c) for c in cs]
    rt = []
    for r in resp:
        for answer_dict in r['answers']:
            for id_, a in answer_dict.items():
                if id_ == 'round': continue
                rt.append({
                    'session_id': r['session_id'], 
                    'participant_id': r['participant_id'], 
                    'round': answer_dict['round'], 
                    'question_id': id_, 
                    'answer': a['answer'], 
                    'reason': a['reason']
                })
    return rt



def export_participant_data(csv_file, botex_db = None):
    """
    Export the participants table from the botex database to a CSV file.

    Parameters:
        csv_file (str): The file path to save the CSV file.
        botex_db (str, optional): The file path to the botex sqlite3 file. 
            If not provided, it will try to read the file name from
            the environment variable BOTEX_DB.

    Returns:
        None (saves the CSV to the specified file path)
    """
    p = read_participants_from_botex_db(botex_db = botex_db)
    with open(csv_file, 'w') as f:
        w = csv.DictWriter(f, p[0].keys())
        w.writeheader()
        w.writerows(p)



def export_response_data(csv_file, botex_db = None):
    """
    Export the responses parsed from the bot conversations in the botex
    database to a CSV file.

    Parameters:
        csv_file (str): The file path to save the CSV file.
        botex_db (str, optional): The file path to the botex sqlite3 file. 
            If not provided, it will try to read the file name from
            the environment variable BOTEX_DB.

    Returns:
        None (saves the CSV to the specified file path)
    """
    
    r = read_responses_from_botex_db(botex_db = botex_db)
    with open(csv_file, 'w') as f:
        w = csv.DictWriter(f, r[0].keys())
        w.writeheader()
        w.writerows(r)
