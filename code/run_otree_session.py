from os import environ
from datetime import datetime, timezone
import sqlite3
from threading import Thread
from random import sample
import logging
logging.basicConfig(level=logging.INFO)

# pip install python-dotenv
from dotenv import load_dotenv
import requests  

from bot import run_bot


SESSION_CONFIG_NAME = 'trust'
PLAYERS = 2

GET = requests.get
POST = requests.post

load_dotenv('secrets.env')
SERVER_URL = environ.get('OTREE_URL')
REST_KEY = environ.get('OTREE_REST_KEY')
BOT_DB_SQLITE = environ.get('BOT_DB_SQLITE')

def setup_bot_db():
    conn = sqlite3.connect(BOT_DB_SQLITE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
    )
    table_exists = cursor.fetchone()
    if not table_exists:
        cursor.execute(
            """
            CREATE TABLE sessions (session_name varchar, session_id char(8), 
            participant_id char(8), is_human integer, url text, 
            time_in varchar, time_out varchar)
            """
        )
        conn.commit()
    cursor.execute(
        """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='conversations'
        """
    )
    table_exists = cursor.fetchone()
    if not table_exists:
        cursor.execute(
            """
            CREATE TABLE conversations 
            (id char(8), bot_parms text, conversation text)
            """
        )
        conn.commit()
    cursor.close()
    return conn

def call_api(method, *path_parts, **params) -> dict:
    path_parts = '/'.join(path_parts)
    url = f'{SERVER_URL}/api/{path_parts}'
    resp = method(url, json=params, headers={'otree-rest-key': REST_KEY})
    if not resp.ok:
        msg = (
            f'Request to "{url}" failed '
            f'with status code {resp.status_code}: {resp.text}'
        )
        raise Exception(msg)
    return resp.json()

session_id = call_api(
    POST, 'sessions', session_config_name=SESSION_CONFIG_NAME, 
    num_participants=PLAYERS
)['code']
part_data = call_api(GET, 'sessions', session_id)['participants']
part_codes = [pd['code'] for pd in part_data]

BASE_URL = SERVER_URL + '/InitializeParticipant/'
urls = [BASE_URL + pc for pc in part_codes]

nbots = int(input("How many bots do you want? "))
if nbots > PLAYERS: raise(Exception(
    f"Wrong entry - bot number cannot be higher than {PLAYERS}."
))
bots_urls = [urls[i] for i in sample(range(PLAYERS), nbots)]
human_urls = list(set(urls) - set(bots_urls))

rows = zip(
    SESSION_CONFIG_NAME*PLAYERS, [session_id]*PLAYERS, 
    part_codes, [x in human_urls for x in urls], urls,
    [datetime.now(timezone.utc)]*PLAYERS
)

conn = setup_bot_db()
cursor = conn.cursor()
cursor.executemany(
    """
    INSERT INTO sessions (
        session_name, session_id, participant_id, is_human, url, time_in) 
    VALUES (?, ?, ?, ?, ?, ?) 
    """, rows
)
conn.commit()
cursor.close()

print("Human URLs:", human_urls)
print("Bot URLs", bots_urls)

threads = [ Thread(target = run_bot, args=(url,)) for url in bots_urls ]
for t in threads: t.start()
for t in threads: t.join()

cursor = conn.cursor()
cursor.execute(
    "UPDATE sessions SET time_out = ? WHERE session_id = ?", 
    (datetime.now(timezone.utc), session_id)
)
conn.commit()
cursor.close()
conn.close()