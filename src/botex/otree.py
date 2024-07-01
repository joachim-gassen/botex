from os import environ
import sqlite3
from threading import Lock, Thread
from random import sample, shuffle
import logging
logging.basicConfig(level=logging.INFO)
from datetime import datetime, timezone
from itertools import compress
import requests

from .bot import run_bot
from .local_llm import LocalLLM


def setup_botex_db(botex_db = None):
    """
    Create a SQLite database to store BotEx data.

    Parameters:
    botex_db (str): The name of a SQLite database file.
        It will be created if it does not exist.
        By default, it will try to read the file name from 
        the environment variable BOTEX_DB.
    """
    if botex_db is None: botex_db = environ.get('BOTEX_DB')
    conn = sqlite3.connect(botex_db)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='participants'"
    )
    table_exists = cursor.fetchone()
    if not table_exists:
        cursor.execute(
            """
            CREATE TABLE participants (session_name varchar, session_id char(8), 
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
 

def init_otree_session(
        config_name, npart, nhumans = 0, 
        is_human = None,
        room_name = None,
        botex_db = None,
        otree_server_url = None,
        otree_rest_key = None
    ):
    """
    Initialize an oTree session with a given number of participants.

    Parameters:
    config_name (str): The name of the oTree session configuration.
    npart (int): The total number of participants.
    nhumans (int): The number of human participants (defaults to zero). Provide
        either nhumans or is_human, but not both.
    is_human (list): A list of booleans indicating whether each participant is human.
        Needs to be the same length as npart. If None (the default), humans 
        (if present) will be randomly assigned.
    room_name (str): The name of the oTree room for the session. If None (the default),
        no room will be used.
    botex_db (str): The name of the SQLite database file to store BotEx data.
        If None (the default), it will be obtained from the environment variable 
        BOTEX_DB. If the database does not exist, it will be created.
    otree_server_url (str): The URL of the oTree server.
        If None (the default), it will be obtained from the environment variable 
        OTREE_SERVER_URL.
    otree_rest_key (str): The API key for the oTree server.
        If None (the default), it will be obtained from the environment variable 
        OTREE_REST_KEY.

    Returns:
    dict with the keys 'session_id', 'participant_code', 'is_human', 
    'bot_urls', and 'human_urls'
    containing the session ID, participant codes, human indicators,
    and the URLs for the human and bot participants.
    """

    def call_api(method, *path_parts, **params) -> dict:
        path_parts = '/'.join(path_parts)
        url = f'{otree_server_url}/api/{path_parts}'
        resp = method(url, json=params, headers={'otree-rest-key': otree_rest_key})
        if not resp.ok:
            msg = (
                f'Request to "{url}" failed '
                f'with status code {resp.status_code}: {resp.text}'
            )
            raise Exception(msg)
        return resp.json()

    if nhumans > 0 and is_human is not None: raise(Exception(
        "Provide either nhumans or is_human, but not both."
    ))

    if is_human is not None:
        if len(is_human) != npart: raise(Exception(
            "Length of is_human must be the same as npart."
        ))
    
    if is_human is None and nhumans > 0:
        is_human = [True]*nhumans + [False]*(npart - nhumans)
        shuffle(is_human)

    if is_human is None and nhumans == 0: is_human = [False]*npart

    if botex_db is None: botex_db = environ.get('BOTEX_DB')
    if otree_server_url is None:
        otree_server_url = environ.get('OTREE_SERVER_URL')
    if otree_rest_key is None:
        otree_rest_key = environ.get('OTREE_REST_KEY')
    
    session_id = call_api(
        requests.post, 'sessions', session_config_name=config_name, 
        num_participants=npart, room_name=room_name
    )['code']
    part_data = sorted(
        call_api(requests.get, 'sessions', session_id)['participants'],
        key=lambda d: d['id_in_session']
    )
    part_codes = [pd['code'] for pd in part_data]

    base_url = otree_server_url + '/InitializeParticipant/'
    urls = [base_url + pc for pc in part_codes]

    rows = zip(
        [config_name]*npart, [session_id]*npart, 
        part_codes, is_human, urls
    )

    conn = setup_botex_db(botex_db)
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO participants (
            session_name, session_id, participant_id, is_human, url) 
            VALUES (?, ?, ?, ?, ?) 
        """, rows
    )
    conn.commit()
    cursor.close()
    return {
        'session_id': session_id, 
        'participant_code': part_codes,
        'is_human': is_human,
        'bot_urls': list(compress(urls, [not x for x in is_human])), 
        'human_urls': list(compress(urls, is_human))
    }


def get_bot_urls(session_id, botex_db = None, already_started = False):
    """
    Get the URLs for the bot participants in an oTree session.

    Parameters:
    session_id (str): The ID of the oTree session.
    botex_db (str): The name of the SQLite database file to store BotEx data.
        If None (the default), it will be obtained from the environment 
        variable BOTEX_DB.

    Returns:
    list: The URLs for the bot participants.
    """

    if botex_db is None: botex_db = environ.get('BOTEX_DB')
    conn = sqlite3.connect(botex_db)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT url,time_in,time_out FROM participants 
        WHERE session_id = ? AND is_human = 0
        """, (session_id,)
    )
    if already_started:
        urls = [row[0] for row in cursor.fetchall() if row[2] is None]
    else:
        urls = [row[0] for row in cursor.fetchall() if row[1] is None]
    cursor.close()
    conn.close()
    return urls

def run_bots_on_session(
        session_id, bot_urls = None, 
        botex_db = None, 
        model = "gpt-4o",
        full_conv_history = False,
        openai_api_key = None,
        already_started = False,
        wait = True,
        local_model_cfg={}
    ):
    """
    Run BotEx bots on an oTree session.

    Parameters:
    session_id (str): The ID of the oTree session.
    bots_urls (list): A list of URLs for the bot participants.
        Will be retrieved from the database if None (the default).
    bot_db (str): The name of the SQLite database file for BotEx data.
        If None (the default), it will be obtained from the environment 
        variable BOTEX_DB.
        full_conv_history (bool): Whether to keep the full conversation history.
        This will increase token use and only work with very short experiments.
        Default is False.
    model (str): The model to use for the bot. Default is "gpt-4-turbo-preview"
        from OpenAI. You will need an OpenAI key and be prepared to pay to 
        use this model. If None (the default), it will be obtained from the environment variable
        OPENAI_API_KEY.
    openai_api_key (str): The API key for the OpenAI service.
    already_started (bool): If True, the function will also run bots that have
        already started but not yet finished. This is useful if bots did not 
        startup properly because of network issues. Default is False.
    wait (bool): If True (the default), the function will wait for the bots to 
        finish.
    local_model_cfg (dict): Configuration for the local model. If model is "local", as a bare minimum it should contain, the "path_to_compiled_llama_server_executable", and "local_model_path" keys.

    Returns: None (bot conversation logs are stored in database)
    """

    if botex_db is None: botex_db = environ.get('BOTEX_DB')
    if openai_api_key is None: openai_api_key = environ.get('OPENAI_API_KEY')
    if bot_urls is None: 
        bot_urls = get_bot_urls(session_id, botex_db, already_started)
    lock = Lock()
    if model == "local":
        local_llm = LocalLLM(**local_model_cfg)
        llm_server = local_llm.start_server()
    else:
        local_llm = None 
    threads = [
        Thread(
            target = run_bot, 
            kwargs = {
                'botex_db': botex_db, 'session_id': session_id, 
                'url': url, 'lock': lock, 'full_conv_history': full_conv_history, 'model': model, 'openai_api_key': openai_api_key, 'local_llm': local_llm
            }
        ) for url in bot_urls 
    ]
    for t in threads: t.start()
    if wait: 
        for t in threads: t.join()
    
    if local_llm:
        assert llm_server, "Local LLM server not started, but should have been."
        local_llm.stop_server(llm_server)


if __name__ == '__main__':
    SESSION_CONFIG_NAME = 'deception'
    PLAYERS = 2
    # pip install python-dotenv
    from dotenv import load_dotenv
    load_dotenv("secrets.env")

    nbots = int(input(
        f"Starting the session {SESSION_CONFIG_NAME} with {PLAYERS} players. " +
        "How many bots do you want? "
    ))
    if nbots > PLAYERS: raise(Exception(
        f"Wrong entry - bot number cannot be higher than {PLAYERS}."
    ))
    sdata =  init_otree_session(
        SESSION_CONFIG_NAME, npart = PLAYERS, nhumans = PLAYERS - nbots
    )

    print("Session ID:", sdata['session_id'])
    print("Human URLs:", sdata['human_urls'])
    print("Bot URLs", sdata['bot_urls'])

    run_bots_on_session(sdata['session_id'], sdata['bot_urls'])
 