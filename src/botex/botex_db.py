import csv
import json
import sqlite3
import logging
from os import environ


def read_participants_from_botex_db(session_id = None, botex_db = None):
    """
    Read the participants table from the BotEx database.

    Args:
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
        session_id = None, botex_db = None
    ):
    """
    Reads the conversations table from the BotEx database. 
    The conversation table contains the messages exchanged 
    with the LLM underlying the bot.

    Returns:
        List of dicts: A list of dictionaries with the conversation data.
    """
    if botex_db is None: botex_db = environ.get('BOTEX_DB')
    conn = sqlite3.connect(botex_db)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    if session_id:
        cursor.execute(
            "SELECT * FROM conversations WHERE session_id = ?", (session_id,)
        )
    else:
        cursor.execute("SELECT * FROM conversations")
    conversations = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return conversations


def export_participant_data(csv_file, botex_db = None):
    """
    Export the participants table from the BotEx database to a CSV file.

    Args:
        csv_file (str): The file path to save the CSV file.
        botex_db (str, optional): The file path to the botex sqlite3 file. 
            If not provided, it will try to read the file name from
            the environment variable BOTEX_DB.
    """
    p = read_participants_from_botex_db(botex_db = botex_db)
    with open(csv_file, 'w') as f:
        w = csv.DictWriter(f, p[0].keys())
        w.writeheader()
        w.writerows(p)



def export_response_data(csv_file, botex_db = None):
    """
    Export the responses parsed from the bot conversations in the BotEx 
    database to a CSV file.

    Args:
        csv_file (str): The file path to save the CSV file.
        botex_db (str, optional): The file path to the botex sqlite3 file. 
            If not provided, it will try to read the file name from
            the environment variable BOTEX_DB.
    """
    
    def retrieve_responses(resp_str):
        try:
            resp_str = resp_str
            start = resp_str.find('{', 0)
            end = resp_str.rfind('}', start)
            resp_str = resp_str[start:end+1]
            cont = json.loads(resp_str, strict = False)
            if 'questions' in cont: return cont['questions']
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
                    if m['content'][:7] == 'Perfect': answers.extend(pot_a)
                    pot_a = None

        ids = []
        round = 1
        for i,a in enumerate(answers):
            ids.append(a['id'])
            c_id = ids.count(a['id'])
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

    cs = read_conversations_from_botex_db(botex_db = botex_db)
    resp = [parse_conversation(c) for c in cs]
    fields = [
        'session_id', 'participant_id', 'round', 
        'question_id', 'answer', 'reason'
    ]
    with open(csv_file, 'w') as f:
        w = csv.writer(f)
        w.writerow(fields)
        for r in resp:
            for a in r['answers']:
                w.writerow([
                    r['session_id'], r['participant_id'], 
                    a['round'], a['id'], a['answer'], a['reason']
                ])
