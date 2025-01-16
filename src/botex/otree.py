import subprocess
import signal
import platform
import psutil
import time
import os 
import shutil
import csv
import tempfile
import sqlite3
from threading import Thread
from random import shuffle
from itertools import compress
import requests
from typing import List

import logging
logger = logging.getLogger("botex")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .bot import run_bot


def setup_botex_db(botex_db = None):
    """
    Create a SQLite database to store BotEx data.

    Parameters:
    botex_db (str): The name of a SQLite database file.
        It will be created if it does not exist.
        By default, it will try to read the file name from 
        the environment variable BOTEX_DB.
    """
    if botex_db is None: botex_db = os.environ.get('BOTEX_DB')
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


def call_otree_api(
        method, *path_parts, 
        otree_server_url = None, otree_rest_key = None, **params
    ) -> dict:
    """
    Calls an oTree API REST endpoint.

    Parameters:
    method (function): The HTTP method to use (e.g., requests.get, requests.post).
    path_parts (list): The endpoints parts of the API URL.
    otree_server_url (str): The URL of the oTree server. Read from environment
        variable OTREE_SERVER_URL if None (the default).
    otree_rest_key (str): The API key for the oTree server. Read from environment
        variable OTREE_REST_KEY if None (the default).
    params (dict): The JSON parameters to send with the request.

    Returns:
    dict: The JSON response from the API.
    """

    if otree_server_url is None:
        otree_server_url = os.environ.get('OTREE_SERVER_URL')
    if otree_rest_key is None:
        otree_rest_key = os.environ.get('OTREE_REST_KEY')

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


def otree_server_is_running(server_url = None, rest_key = None) -> bool:
    """
    Check if an oTree server is running.

    Args:
        server_url (str): The URL of the oTree server. Read from environment
            variable OTREE_SERVER_URL if None (the default).
        rest_key (str): The API key for the oTree server. Read from environment
            variable OTREE_REST_KEY if None (the default).

    Returns:
        True if the server is running, False otherwise.
    """
    try: 
        data = call_otree_api(
            requests.get, 'otree_version', 
            otree_server_url=server_url, otree_rest_key=rest_key
        )
    except:
        data = {'error': "No API response"}
    return 'version' in data

    
def start_otree_server(
        project_path = None,
        port = None, 
        log_file = None,
        auth_level = None, 
        rest_key = None,
        admin_password = None,
        timeout = 5
    ) -> subprocess.Popen:
    """
    Start an oTree server in a subprocess.

    Args:
        project_path (str, optional): Path to your oTree project folder.
            If None (the default), it will be obtained from the environment
            variable OTREE_PROJECT_PATH.
        port (int, optional): The port to run the server on. If None 
            (the default), it will first try to read from the 
            environment variable OTREE_PORT. It that is not set. it 
            will default to 8000.
        log_file (str, optional): Path to the log file. If None 
            (the default), it will first be tried to read from the
            environment variable OTREE_LOG_FILE. If that is not set,
            it will default to 'otree.log'.
        auth_level (str, optional): The authentication level for the oTree 
            server. It is set by environment variable OTREE_AUTH_LEVEL. 
            The default is None, which will leave this environment variable
            unchanged. if you use 'DEMO' or 'STUDY', the environment variable
            will be set accordingly and you need to provide a rest key
            in the argument 'rest_key' below.
        rest_key (str, optional): The API key for the oTree server.
            If None (the default), it will be obtained from the environment
            variable OTREE_REST_KEY.
        admin_password (str, optional): The admin password for the oTree server.
            For this to work, `settings.py` in the oTree project needs to read
            the password from the environment variable OTREE_ADMIN_PASSWORD
            (which is normally the case).
        timeout (int, optional): Timeout in seconds to wait for the 
            server. Defaults to 5.

    Returns:
        A subprocess object.
    
    Raises:
        Exception: If the oTree server does not start within the timeout.
    """
    if project_path is None:
        project_path = os.environ.get('OTREE_PROJECT_PATH')
        if project_path is None:
            raise Exception('No oTree project path provided.')
    if port is None: port = os.environ.get('OTREE_PORT', 8000)
    if log_file is None: log_file = os.environ.get('OTREE_LOG_FILE', 'otree.log')
    otree_log = open(log_file, 'w')
    if auth_level is not None: 
        os.environ['OTREE_AUTH_LEVEL'] = auth_level
        if rest_key is not None:
            os.environ['OTREE_REST_KEY'] = rest_key
        if admin_password is not None:
            os.environ['OTREE_ADMIN_PASSWORD'] = admin_password 


    if platform.system() == "Windows":
        otree_server = subprocess.Popen(
            ["otree", "devserver", str(port)], cwd=project_path,
            stderr=otree_log, stdout=otree_log,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        otree_server = subprocess.Popen(
            ["otree", "devserver", str(port)], cwd=project_path,
            stderr=otree_log, stdout=otree_log
        )
    otree_server_url = f'http://localhost:{port}'
    os.environ['OTREE_SERVER_URL'] = otree_server_url

    # Access oTree API to check if server is running
    time_out = time.time() + timeout
    while True:
        if otree_server_is_running(rest_key = rest_key):
            logger.info(
                "oTree server started successfully "
                f"with endpoint '{otree_server_url}'"
            )
            break
        else:
            if time.time() > time_out:
                logger.error(
                    f"oTree endpoint '{otree_server_url}' did not respond "
                    f"within {timeout} seconds. Exiting."
                )
                raise Exception('oTree server did not start.')
            time.sleep(1)
    return otree_server


def stop_otree_server(otree_server: subprocess.Popen) -> int:
    """
    Stop an oTree server subprocess.

    Args:
        otree_server (subprocess): The subprocess object to be terminated.

    Returns:
        The return code of the oTree subprocess
    """
    otree_running = otree_server.poll() is None
    if otree_running: 
        proc = psutil.Process(otree_server.pid)
        if platform.system() == "Windows":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            proc.wait()
        else: 
            proc.children()[0].send_signal(signal.SIGKILL)
            otree_server.kill()
            otree_server.wait()
        logger.info("oTree server stopped.")
    else:
        logger.warning('oTree server already stopped.')
    return otree_server.poll()

 
def get_session_configs(
        otree_server_url: str | None = None,
        otree_rest_key: str | None = None
    ) -> dict:
    """
    Get the session configurations from an oTree server.

    Args:
        otree_server_url (str): The URL of the oTree server. Read from 
            environment variable OTREE_SERVER_URL if None (the default).
        otree_rest_key (str): The API key for the oTree server. Read from 
            environment variable OTREE_REST_KEY if None (the default).

    Returns:
        The session configurations.
    """

    return call_otree_api(
        requests.get, 'session_configs', 
        otree_server_url=otree_server_url, otree_rest_key=otree_rest_key
    )

def init_otree_session(
        config_name: str,
        npart: int,
        nhumans: int = 0, 
        is_human: List[bool] | None = None,
        room_name: str | None = None,
        botex_db: str | None = None,
        otree_server_url: str | None = None,
        otree_rest_key: str | None = None,
        modified_session_config_fields: dict | None = None,
    ) -> dict:
    """
    Initialize an oTree session with a given number of participants.

    Args:
        config_name (str): The name of the oTree session configuration.
        npart (int): The total number of participants.
        nhumans (int): The number of human participants (defaults to zero.
            Provide either nhumans or is_human, but not both.
        is_human (list): A list of booleans indicating whether each participant 
            is human. Needs to be the same length as npart. If None (the 
            default), humans (if present) will be randomly assigned.
        room_name (str): The name of the oTree room for the session. If None 
            (the default), no room will be used.
        botex_db (str): The name of the SQLite database file to store BotEx     
            data. If None (the default), it will be obtained from the 
            environment variable BOTEX_DB. If the database does not exist, it 
            will be created.
        otree_server_url (str): The URL of the oTree server. If None (the 
            default), it will be obtained from the environment variable 
            OTREE_SERVER_URL.
        otree_rest_key (str): The API key for the oTree server. If None (the 
            default), it will be obtained from the environment variable 
            OTREE_REST_KEY.
        modified_session_config_fields (dict): A dictionary of fields to modify 
            in the the oTree session config. Default is None. 

    Returns:
        dict with the keys 'session_id', 'participant_code', 'is_human', 
            'bot_urls', and 'human_urls' containing the session ID, participant 
            codes, human indicators, and the URLs for the human and bot 
            participants.
    """

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

    if botex_db is None: botex_db = os.environ.get('BOTEX_DB')
    
    if otree_server_url is None:
        otree_server_url = os.environ.get('OTREE_SERVER_URL')
    
    session_id = call_otree_api(
        requests.post, 'sessions', 
        otree_server_url=otree_server_url, otree_rest_key=otree_rest_key, 
        session_config_name=config_name, 
        num_participants=npart, room_name=room_name,
        modified_session_config_fields=modified_session_config_fields
    )['code']
    part_data = sorted(
        call_otree_api(
            requests.get, 'sessions', session_id,
            otree_server_url=otree_server_url, otree_rest_key=otree_rest_key 
        )['participants'],
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


def get_bot_urls(
        session_id: str,
        botex_db: str | None = None,
        already_started: bool = False
    ) -> List[str]:
    """
    Get the URLs for the bot participants in an oTree session.

    Args:
        session_id (str): The ID of the oTree session.
        botex_db (str): The name of the SQLite database file to store BotEx 
            data. If None (the default), it will be obtained from the 
            environment variable BOTEX_DB.
        already_started (bool): If True, the function will also run bots that 
            have already started but not yet finished. This is useful if bots 
            did not startup properly because of network issues. Default is 
            False.

    Returns:
        List of URLs for the bot participants
    """

    if botex_db is None: botex_db = os.environ.get('BOTEX_DB')
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
        session_id: str,
        bot_urls: List[str] | None = None, 
        botex_db: str | None = None, 
        model: str = "gpt-4o-2024-08-06",
        api_key: str | None = None,
        api_base: str | None = None,
        throttle: bool = False,
        full_conv_history: bool = False,
        user_prompts: dict | None = None,
        already_started: bool = False,
        wait: bool = True,
        **kwargs
    ) -> None | List[Thread]:
    """
    Run botex bots on an oTree session.

    Args:
        session_id (str): The ID of the oTree session.
        bot_urls (list): A list of URLs for the bot participants.
            Will be retrieved from the database if None (the default).
        botex_db (str): The name of the SQLite database file for BotEx data.
            If None (the default), it will be obtained from the environment 
            variable BOTEX_DB.
        model (str): The model to use for the bot. Default is 
            `gpt-4o-2024-08-06` from OpenAI vie LiteLLM. It needs to be a model 
            that supports structured outputs. For OpenAI, these are 
            gpt-4o-mini-2024-07-18 and later or gpt-4o-2024-08-06 and later. If 
            you use a commercial model, You need to provide an API key in the 
            parameter `api_key` and be prepared to pay to use this model.
            
            If you want to use local models, we suggest that you use llama.cpp, 
            In this case, set this string to `lamacpp` and set the URL of your 
            llama.cpp server in `api_base`. If you want botex to start the  llama.cpp server for you, run `start_llamacpp_sever()` prior to 
            running run_bots_on_session().
        api_key (str): The API key for the model that you use. If None (the 
            default), it will be obtained from environment variables by liteLLM 
            (e.g., OPENAI_API_KEY or GEMINI_API_KEY). 
        api_base (str): The base URL for the llm server. Default is None not to
            interfere with the default LiteLLM behavior. If you want to use a 
            local model with llama.cpp and if you have not explicitly set this 
            parameter, it will default to `http://localhost:8080`, the default 
            url for the llama.cpp server.
        throttle (bool): Whether to slow down the bot's requests. Slowing done 
            the requests can help to avoid rate limiting. Default is False. The 
            bot will switch to `throttle=True` when LiteLLM is used and 
            completion requests raise exceptions.
        full_conv_history (bool): Whether to keep the full conversation history.
            This will increase token use and only work with very short 
            experiments. Default is False.
        user_prompts (dict): A dictionary of user prompts to override the 
            default prompts that the bot uses. The keys should be one or more 
            of the following:
            
            [`start`, `analyze_first_page_no_q`, `analyze_first_page_q`, 
            `analyze_page_no_q`, `analyze_page_q`,
            `analyze_page_no_q_full_hist`, `analyze_page_q_full_hist`, 
            `page_not_changed`, `system`, `system_full_hist`, `resp_too_long`, 
            `json_error`, `end`, `end_full_hist`].
            
            If a key is not present in  the dictionary, the default prompt will 
            be used. If a key that is not in the default prompts is present in 
            the dictionary, then the bot will exit with a warning and not run 
            to make sure that the user is aware of the issue.
        already_started (bool): If True, the function will also run bots that 
            have already started but not yet finished. This is useful if bots 
            did not startup properly because of network issues. Default is 
            False.
        wait (bool): If True (the default), the function will wait for the bots 
            to finish.
        kwargs (dict): Additional keyword arguments to pass on to
            `litellm.completion()`.
        
    Returns:
        None (bot conversation logs are stored in database) if wait is True. A list of Threads running the bots if wait is False.

    ??? tip "Additional details"
    
        When running local models via llama.cpp, if you would like 
            botex to start the llama.cpp server for you, 
            run `start_llamacpp_server()` to start up the server prior to
            running `run_bots_on_session()`.

    ??? example "Example Usage"
    
        - Running botex with the default model (`gpt-4o-2024-08-06`)
        
        ```python
        run_bots_on_session(
            session_id="your_session_id",
            botex_db="path/to/botex.sqlite3",
            api_key="your_openai_api_key",
            # Other parameters if and as needed
        )
        ```

        - Using a specific model supported by LiteLLM

        ```python    
        run_bots_on_session(
            session_id="your_session_id",
            botex_db="path/to/botex.sqlite3",
            model="gemini/gemini-1.5-flash",
            api_key="your_gemini_api_key",
            # Other parameters if and as needed
        )
        ```

        - Using a local model with BotEx starting the llama.cpp server
    
        ```python
        llamacpp_config = {
            "server_path": "/path/to/llama/server",
            "local_llm_path": "/path/to/local/model",
            # Additional configuration parameters if and as needed
        }
        process_id = start_llamacpp_server(llamacpp_config)
        run_bots_on_session(
            session_id="your_session_id",
            botex_db="path/to/botex.sqlite3",
            model="llamacpp",
            # Other parameters if and as needed
        )
        stop_llamacpp_server(process_id)
        ```

        - Using a local model with an already running llama.cpp server that 
            uses a URL different from the default (if you are using the 
            default "http://localhost:8080", you can simply omit the `api_base` 
            parameter)
    
        ```python
        run_bots_on_session(
            session_id="your_session_id",
            botex_db="path/to/botex.sqlite3",
            model = "llamacpp",
            api_base = "http://yourserver:port"},
            # Other parameters if and as needed
        )
        ```
    """
    if botex_db is None: botex_db = os.environ.get('BOTEX_DB')
    if api_key is None and 'openai_api_key' in kwargs: 
        api_key = kwargs.pop('openai_api_key')
    if bot_urls is None: 
        bot_urls = get_bot_urls(session_id, botex_db, already_started)
    
    otree_url = bot_urls[0].split('/InitializeParticipant/')[0]
    logger.info(
        f"Running bots on session {session_id}. "
        f"You can monitor the session at {otree_url}/SessionMonitor/{session_id}"
    )
    thread_kwargs = {
        'botex_db': botex_db, 'session_id': session_id, 
        'full_conv_history': full_conv_history, 
        'model': model, 'api_key': api_key,
        'api_base': api_base,
        'user_prompts': user_prompts,
        'throttle': throttle
    }
    thread_kwargs.update(kwargs)
    threads = [
        Thread(
            target = run_bot, 
            kwargs = dict(thread_kwargs, **{'url': url})
        ) for url in bot_urls 
    ]
    for t in threads: t.start()
    if wait: 
        for t in threads: t.join()
    else:
        return threads

def run_single_bot(
    url: str,
    session_name: str = "unknown",
    session_id: str = "unknown", 
    participant_id: str = "unknown",
    botex_db: str | None = None,
    model: str = "gpt-4o-2024-08-06",
    api_key: str | None = None,
    api_base: str | None = None,
    throttle: bool = False, 
    full_conv_history: bool = False,
    user_prompts: dict | None = None,
    wait: bool = True,
    **kwargs
) -> None | Thread:
    """
    Runs a single botex bot manually.

    Args:
        url (str): The participant URL to start the bot on.
        session_name (str): The name of the oTree session. Defaults to "unknown"
        session_id (str): The oTree ID of the oTree session. Defaults to 
            "unknown".
        participant_id (str): The oTree ID of the participant. Defaults to 
            "unknown".
        botex_db (str): The name of the SQLite database file to store botex 
            data.
        full_conv_history (bool): Whether to keep the full conversation history.
            This will increase token use and only work with very short 
            experiments. Default is False.
        model (str): The model to use for the bot. Default is 
            `gpt-4o-2024-08-06` from OpenAI vie LiteLLM. It needs to be a model 
            that supports structured outputs. For OpenAI, these are 
            gpt-4o-mini-2024-07-18 and later or gpt-4o-2024-08-06 and later. If 
            you use a commercial model, You need to provide an API key in the 
            parameter `api_key` and be prepared to pay to use this model.
            
            If you want to use local models, we suggest that you use llama.cpp, 
            In this case, set this string to `lamacpp` and set the URL of your 
            llama.cpp server in `api_base`. If you want botex to start the  llama.cpp server for you, run `start_llamacpp_sever()` prior to 
            running run_bots_on_session().
        api_key (str): The API key for the model that you use. If None (the 
            default), it will be obtained from environment variables by liteLLM 
            (e.g., OPENAI_API_KEY or GEMINI_API_KEY). 
        api_base (str): The base URL for the llm server. Default is None not to
            interfere with the default LiteLLM behavior. If you want to use a 
            local model with llama.cpp and if you have not explicitly set this 
            parameter, it will default to `http://localhost:8080`, the default 
            url for the llama.cpp server.
        throttle (bool): Whether to slow down the bot's requests. Slowing done 
            the requests can help to avoid rate limiting. Default is False. The 
            bot will switch to `throttle=True` when LiteLLM is used and 
            completion requests raise exceptions.
        full_conv_history (bool): Whether to keep the full conversation history.
            This will increase token use and only work with very short 
            experiments. Default is False.
        user_prompts (dict): A dictionary of user prompts to override the 
            default prompts that the bot uses. The keys should be one or more 
            of the following:
            
            [`start`, `analyze_first_page_no_q`, `analyze_first_page_q`, 
            `analyze_page_no_q`, `analyze_page_q`,
            `analyze_page_no_q_full_hist`, `analyze_page_q_full_hist`, 
            `page_not_changed`, `system`, `system_full_hist`, `resp_too_long`, 
            `json_error`, `end`, `end_full_hist`].
            
            If a key is not present in  the dictionary, the default prompt will 
            be used. If a key that is not in the default prompts is present in 
            the dictionary, then the bot will exit with a warning and not run 
            to make sure that the user is aware of the issue.
        wait (bool): If True (the default), the function will wait for the bots 
            to finish.
        kwargs (dict): Additional keyword arguments to pass on to
            `litellm.completion()`.
        
    Returns:
        None (conversation is stored in the botex database) if wait is True.
            The Thread running the bot if wait is False.

    Notes:

    -   When running local models via llama.cpp, if you would like 
        botex to start the llama.cpp server for you, 
        run `start_llamacpp_server()` to start up the server prior to
        running `run_bots_on_session()`.
    
    ??? example "Example Usage"

        - Using a model via LiteLLM

        ```python
        run_single_bot(
            url="your_participant_url",
            session_name="your_session_name",
            session_id="your_session_id",
            participant_id="your_participant_id",
            botex_db="path/to/botex.sqlite3",
            model="a LiteLLM model string, e.g. 'gemini/gemini-1.5-flash'",
            api_key="the API key for your model provide",
            # Other parameters if and as needed
        )
        ```


        - Using a local model with an already running llama.cpp server
        
        ```python
        run_single_bot(
            url="your_participant_url",
            session_name="your_session_name",
            session_id="your_session_id",
            participant_id="your_participant_id",
            botex_db="path/to/botex.sqlite3",
            model="llamacpp",
            api_base="http://yourhost:port" # defaults to http://localhost:8080
            # Other parameters if and as needed
        )
        ```

        - Using a local model with BotEx starting the llama.cpp server

        ```python
        llamacpp_config = {
            "server_path": "/path/to/llama/server",
            "local_llm_path": "/path/to/local/model",
            # Additional configuration parameters if and as needed
        }
        process_id = start_llamacpp_server(llamacpp_config)
        run_single_bot(
            url="your_participant_url",
            session_name="your_session_name",
            session_id="your_session_id",
            participant_id="your_participant_id",
            botex_db="path/to/botex.sqlite3",
            model="llamacpp",
            # Other parameters if and as needed
        )
        stop_llamacpp_server(process_id)
        ```
    """
    if api_base is not None:
        kwargs['api_base'] = api_base

    if botex_db is None: botex_db = os.environ.get('BOTEX_DB')
    if api_key is None and 'openai_api_key' in kwargs: 
        api_key = kwargs.pop('openai_api_key')
    
    kwargs['api_key'] = api_key
    is_human = 0

    conn = setup_botex_db(botex_db)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO participants (
            session_name, session_id, participant_id, is_human, url) 
            VALUES (?, ?, ?, ?, ?) 
        """, (session_name, session_id, participant_id, is_human, url,)
    )
    conn.commit()
    cursor.close()
    if wait:
        run_bot(
            botex_db = botex_db, 
            session_id = session_id, 
            url = url, 
            model = model, 
            throttle = throttle, 
            full_conv_history = full_conv_history,
            user_prompts = user_prompts,
            **kwargs
        )
    else:
        return Thread(
            target = run_bot, 
            kwargs = dict(
                botex_db = botex_db, 
                session_id = session_id, 
                url = url, 
                model = model, 
                throttle = throttle, 
                full_conv_history = full_conv_history,
                user_prompts = user_prompts,
                **kwargs
            )
        )
    

def export_otree_data(
        csv_file: str,
        server_url: str | None = None, 
        admin_name: str | None = "admin", 
        admin_password: str | None = None,
        time_out: int | None = 10
    ) -> None:
    """
    Export wide data from an oTree server.

    Args:
        csv_file (str): Path to the CSV file where the data should be stored.
        server_url (str, optional): URL of the oTree server. If None 
            (the default), the function will try to use the oTree server URL 
            from the environment variable OTREE_SERVER_URL.
        admin_name (str, optional): Admin username. Defaults to "admin".
        admin_password (str, optional): Admin password. If None (the default),
            the function will try to use the oTree admin password from the 
            environment variable OTREE_ADMIN_PASSWORD.
        time_out (int, optional): Timeout in seconds to wait for the download. 
            Defaults to 10.

    Raises:
        Exception: If the download does not succeed within the timeout.

    Returns
        None (data is stored in the CSV file).
    
    Detail:
        The function uses Selenium and a headless Chrome browser to download 
        the CSV file. Ideally, it would use an oTree API endpoint instead.
    """

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    with tempfile.TemporaryDirectory() as tmp_dir:
        prefs = {"download.default_directory": tmp_dir}
        chrome_options.add_experimental_option("prefs", prefs)
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_window_size(1920, 1400)
        if server_url is None:
            server_url = os.getenv("OTREE_SERVER_URL")
        if admin_password is None:
            admin_password = os.getenv("OTREE_ADMIN_PASSWORD")

        export_url = f"{server_url}/export"
        driver.get(export_url)
        current_url = driver.current_url
        if "login" in current_url:
            driver.find_element(By.ID, "id_username").send_keys(admin_name)
            driver.find_element(By.ID, "id_password").send_keys(admin_password)
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "btn-login"))
            )
            submit_button.click()
            WebDriverWait(driver, 10).until(EC.url_changes(current_url))
            driver.get(export_url)
        
        download_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "wide-csv"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true)", download_link)
        download_link.click()

        time_out = time.time() + time_out
        while True:            
            time.sleep(1)
            csv_files = [f for f in os.listdir(tmp_dir) if f.endswith(".csv")]
            if len(csv_files) == 1:
                shutil.move(f"{tmp_dir}/{csv_files[0]}", csv_file)
                logger.info("oTree CSV file downloaded.")
                break
            else:
                if time.time() > time_out:
                    logger.error("oTree CSV file download failed.")
                    break
        driver.quit()


def normalize_otree_data(
    otree_csv_file: str, 
    var_dict: dict | None = {
        'participant': {
            'code': 'participant_code', 
            'time_started_utc': 'time_started_utc',
            '_current_app_name': 'current_app', 
            '_current_page_name': 'current_page',
        },
        'session': {
            'code': 'session_code'
        }
    },
    store_as_csv: bool = False,
    data_exp_path: str | None = '.', 
    exp_prefix: str | None = '',
) -> dict:
    """
    Normalize oTree data from wide to long format, then reshape it into a set 
    of list-of-dicts structures. Optionally save it to a set of CSV files.

    Args:
        otree_csv_file (str): Path to a wide multi app oTree CSV file.
        var_dict (dict, optional): A dict to customize the exported data. See
            detail section.
        store_as_csv (bool, optional): Whether to store the normalized data as
            CSV files. Defaults to False.
        data_exp_path (str, optional): Path to the folder where the normalized
            CSV files should be stored. Defaults to '.' (current folder).
        exp_prefix (str, optional): Prefix to be used for the CSV file names. 
            Defaults to '' (no prefix).

    Returns:
        A dict whose keys are table names (e.g. 'session', 'participant', 
            'myapp_group', 'myapp_player', etc.) and whose values are lists of 
            dictionaries (i.e., row data).
    
    ??? tip "Additional details"
        The var_dict parameter is a dictionary that allows to customize the
        exported data. The keys of the dictionary are the names of the oTree
        apps. The values are dictionaries that map the original column names to
        the desired column names. The keys of these inner dictionaries are the
        original column names and the values are the desired column names. All
        variables that are not included in the dict are omitted from the output.
        The 'participant' and 'session' keys are reserved for the participant 
        and session data, respectively.
    """

    # The function is based on the naming conventions of oTree CSV files.
    # oTree uses multi-level headers in the CSV file, where each level is
    # separated by a dot. 

    # The general flow of the function is as follows:
    # 1) Read the CSV file and extract the multi-level headers.
    # 2) Pivot the data to long format by flattening wide columns into rows of   
    #     [observation, level_1..4, value].
    # 3) Extract participant and session data.
    # 4) Separate the remaining long data by app and sub-level, pivoting each
    #    resulting data set back into wide format and add the appropriate
    #    keys from participant and session data.
    #    - subsession (should be empty since subsessions seem to be equal to 
    #      rounds, tbc)
    #    - group (merge with session data on participant_code to create key, 
    #      only keep if it contains data)
    #    - player (rename id_in_group to player_id)  
    # 5) Optionally store the data as CSV files.

    # --------------------------------------------------------------------------
    # Helper functions
    # --------------------------------------------------------------------------

    def extract_data(var, stacked_data, var_dict):
        relevant = [
            d for d in stacked_data if d['level_1'] == var 
        ]
        var_dict = var_dict.get(var)
        if var in ['participant', 'session']:
            # exclude not requested rows
            relevant = [
                d for d in relevant if d['level_2'] in var_dict.keys()
            ]
            # Remap level_2 column names
            for item in relevant:
                item['level_2'] = var_dict[item['level_2']]

        # Build pivot result as dict {observation -> one row dict}
        pivoted = {}
        for item in relevant:
            obs = item['observation']
            col = item['level_2']
            val = item['value']
            if obs not in pivoted:
                pivoted[obs] = {'observation': obs}
            # Only keep first occurrence if duplicates exist
            if col not in pivoted[obs]:
                pivoted[obs][col] = val

        return list(pivoted.values())

    def index_to_participant_code(data_list, obs_to_pcode):
        out = []
        for row in data_list:
            obs = row['observation']
            new_row = dict(row)
            new_row['participant_code'] = obs_to_pcode.get(obs, None)
            del new_row['observation']
            out.append(new_row)
        return out

    def try_convert_number(x):
        if x is None:
            return None
        # Already a number? (in case we call this multiple times)
        if isinstance(x, (int, float)):
            return x
        # Attempt int -> float -> fallback str
        try:
            return int(x)
        except (ValueError, TypeError):
            pass
        try:
            return float(x)
        except (ValueError, TypeError):
            pass
        return str(x)

    def convert_columns(data_list, keys=None):
        missing_keys = set()
        if keys:
            missing_keys = set(keys) - set(data_list[0].keys())
        for row in data_list:
            for k, v in row.items():
                if k not in ("observation",):  # do not convert observation index
                    row[k] = try_convert_number(v)
            for k in missing_keys:
                row[k] = '' 
        return data_list
 
    def unify_dict_keys(rows):
        seen_keys = []
        for d in rows:
            for k in d.keys():
                if k not in seen_keys:
                    seen_keys.append(k)
        new_rows = []
        for d in rows:
            new_d = {}
            for k in seen_keys:
                new_d[k] = d.get(k, '') 
            new_rows.append(new_d)
        return new_rows

    def reorder_columns(data_list, first_cols):
        out = []
        for row in data_list:
            new_row = {}
            # keep track of which keys got placed
            placed = set()
            # place the "first_cols" in order
            for c in first_cols:
                if c in row:
                    new_row[c] = row[c]
                    placed.add(c)
            # place remaining
            for c in row:
                if c not in placed:
                    new_row[c] = row[c]
            out.append(new_row)
        return out

    
    def write_dicts_to_csv(dict_rows, file_path):
        if not dict_rows:
            # If empty, write just an empty file or possibly only headers
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                pass
            return
        fieldnames = list(dict_rows[0].keys())
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(dict_rows)


    # --------------------------------------------------------------------------
    # Main code
    # --------------------------------------------------------------------------

    # --- 1) Read the CSV file and extract the multi-level headers -------------

    with open(otree_csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        all_rows = list(reader)
    if not all_rows:
        raise ValueError(f"CSV file {otree_csv_file} is empty or invalid.")

    headers = all_rows[0]
    data_rows = all_rows[1:]
    multi_headers = [tuple(h.split('.')) for h in headers]


    # --- 2) Pivot the data to long format -------------------------------------

    processed_rows = []
    for row_idx, row in enumerate(data_rows):
        row_dict = {}
        for col_idx, val in enumerate(row):
            key_tuple = list(multi_headers[col_idx])
            while len(key_tuple) < 4:
                key_tuple.append(None)
            row_dict[tuple(key_tuple)] = val
        processed_rows.append(row_dict)

    stacked_data = []
    for obs_idx, row_dict in enumerate(processed_rows):
        for (lvl1, lvl2, lvl3, lvl4), val in row_dict.items():
            stacked_data.append({
                'observation': obs_idx,
                'level_1': lvl1,
                'level_2': lvl2,
                'level_3': lvl3,
                'level_4': lvl4,
                'value': val
            })

    all_level1 = set(d['level_1'] for d in stacked_data if d['level_1'])
    all_level1 = all_level1 - {'participant', 'session'}
    apps = sorted(list(all_level1))

    # Ensure var_dict has entries for each discovered app (even if empty).
    for app in apps:
        if app not in var_dict:
            var_dict[app] = {}


    # --- 3) Extract participant and session data ------------------------------

    participant_data = extract_data('participant', stacked_data, var_dict)
    participant_data = convert_columns(participant_data)

    # Build a map: obs -> participant_code
    obs_to_participant_code = {}
    for row in participant_data:
        # We expect 'participant_code' in these rows
        if 'participant_code' in row:
            obs_to_participant_code[row['observation']] = row['participant_code']

    session_data = extract_data('session', stacked_data, var_dict)
    session_data = convert_columns(session_data)
    session_data = index_to_participant_code(session_data, obs_to_participant_code)
    
    for row in participant_data: row.pop('observation')
    participant_data = reorder_columns(participant_data, ['participant_code'])
    
    final_tables = {
        'participant': participant_data,
        'session': session_data,
    }

    # --- 4) Separate the remaining long data by app and sub-level -------------

    # For convenience, gather all unique level_3 for each (level_1 == app).
    # Typically level_3 is 'subsession', 'group', 'player', etc.
    for app in apps:
        logger.info(f"Normalize data for oTree app: '{app}'")
        app_level_3 = sorted(set(
            d['level_3'] for d in stacked_data if d['level_1'] == app and d['level_3']
        ))

        for group_name in app_level_3:
            # Filter data for this app & group
            relevant = [
                d for d in stacked_data
                if d['level_1'] == app and d['level_3'] == group_name
            ]
            if not relevant:
                continue
            
            # Check whether the user provided a custom variable dictionary
            # for this app and group 

            group_dict = var_dict[app].get(group_name, None)
            if group_dict:
                # exclude not requested rows
                struct_vars = [
                    'id_in_group', 'id_in_subsession', 'round_number'
                ]
                relevant = [
                    d for d in relevant if (
                        d['level_4'] in group_dict.keys() or
                        d['level_4'] in struct_vars
                    )
                ]
                # Remap level_4 column names
                for item in relevant:
                    if item['level_4'] not in struct_vars:
                        item['level_4'] = group_dict[item['level_4']]

            pivoted = {}
            cols = set()
            for item in relevant:
                obs = item['observation']
                try:
                    rnd = int(item['level_2'])  # round number
                except (ValueError, TypeError):
                    rnd = None

                cols.add(item['level_4'])
                if item['value'] not in (None, ''):
                    col = item['level_4']
                    val = item['value']
                    key = (obs, rnd)

                    if key not in pivoted:
                        pivoted[key] = {
                            'observation': obs,
                            'round': rnd
                        }
                    if col and col not in pivoted[key]:
                        pivoted[key][col] = val

            pivoted_list = unify_dict_keys(list(pivoted.values()))
            out_df_rows = convert_columns(pivoted_list, cols)
            out_df_rows = index_to_participant_code(
                out_df_rows, obs_to_participant_code
            )
            table_name = f"{app}_{group_name}"  
        
            if group_name == 'subsession':
                # This code assumes that subsesions are equal to rounds.
                # This implies that round_number' and 'round' columns should 
                # match and that the resulting data should have 3 columns.
                col_names = out_df_rows[0].keys() if out_df_rows else []
                if len(col_names) != 3:
                    logger.error(
                        f"Error {app} data extraction: app seems to contain "
                        "more subsessions than rounds or subsession level data."
                    )
                    raise ValueError(
                        f"Error in {app} data extraction: app seems to contain "
                        "more subsessions than rounds."
                    )
                for row in out_df_rows:
                    if 'round_number' in row and row['round_number'] != row['round']:
                        logger.error(
                            f"Error {app} data extraction: subsession round_number "
                            "does not match inferred round."
                        )
                        raise ValueError(
                            f"Error in {app} data extraction: subsession round_number "
                            "does not match inferred round."
                        )
                # No data in subsession, so skip storing
                continue

            elif group_name == 'group':
                # group data might or might not have data
                # (only if there's more than one group or if there are 
                # group-level variables)

                sess_index = {}
                for srow in session_data:
                    pcode = srow.get('participant_code', None)
                    sess_index[pcode] = srow

                merged_group = []
                cols = set()
                for row in out_df_rows:
                    pcode = row.get('participant_code', None)
                    newrow = dict(row)
                    if pcode in sess_index:
                        # merge session data into newrow
                        for k, v in sess_index[pcode].items():
                            # do not overwrite if we already have something
                            if k not in ('participant_code', 'observation', 'round'):
                                cols.add(k)
                                newrow[k] = v
                    merged_group.append(newrow)
                out_df_rows = merged_group

                # Check if 'id_in_subsession' is all 1 - meaning there is only 
                # one group per session
                all_id1 = True
                for row in out_df_rows:
                    if row.get('id_in_subsession') != 1:
                        all_id1 = False
                        break

                if all_id1:
                    # drop ['id_in_subsession', 'participant_code']
                    cleaned = []
                    for row in out_df_rows:
                        newrow = dict(row)
                        newrow.pop('id_in_subsession', None)
                        newrow.pop('participant_code', None)
                        cleaned.append(newrow)
                    out_df_rows = cleaned

                    # If after dropping columns we are left with only 2 columns 
                    # (session_code, round), there is no group level data
                    if out_df_rows:
                        col_count = len(out_df_rows[0])
                        if col_count == 2:
                            # skip storing
                            continue
                else:
                    # rename id_in_subsession -> group_id
                    # build a map of group_id to participant_code
                    cleaned = []
                    group_participant_map = []
                    for row in out_df_rows:
                        newrow = dict(row)
                        newmap = dict()
                        newrow['group_id'] = newrow.pop('id_in_subsession')
                        newmap['participant_code'] = newrow.pop('participant_code')
                        newmap['round'] = newrow['round']
                        newmap['group_id'] = newrow['group_id']
                        cleaned.append(newrow)
                        group_participant_map.append(newmap)
                    out_df_rows = cleaned

                # reorder columns
                col_order = ['session_code', 'round']
                if not all_id1: col_order.append('group_id')
                out_df_rows = convert_columns(
                    reorder_columns(out_df_rows, col_order),
                    cols
                )

                # Deduplicate
                unique_rows = []
                seen = set()
                for row in out_df_rows:
                    # convert to a tuple of items
                    row_tup = tuple(sorted(row.items()))
                    if row_tup not in seen:
                        seen.add(row_tup)
                        unique_rows.append(row)
                out_df_rows = unique_rows

                final_tables[table_name] = out_df_rows

            elif group_name == 'player':
                # rename id_in_group -> player_id
                # and merge with group_participant_map if it exists
                cleaned = []
                for row in out_df_rows:
                    newrow = dict(row)
                    newrow['player_id'] = newrow.pop('id_in_group')
                    if not all_id1:
                        for m in group_participant_map:
                            if  m['round'] == newrow['round'] and \
                                m['participant_code'] == newrow['participant_code']:
                                newrow['group_id'] = m['group_id']
                                break
                    cleaned.append(newrow)
                out_df_rows = cleaned
                # reorder
                if not all_id1:
                    col_order = ['participant_code', 'round', 'group_id', 'player_id']
                else:
                    col_order = ['participant_code', 'round', 'player_id']
                out_df_rows = reorder_columns(
                    out_df_rows, col_order
                )
                final_tables[table_name] = out_df_rows

            else:
                # This should not happen - but if it does, store the data as is
                logger.warning(
                    f"Unrecognized level name '{group_name}' in app '{app}'."
                )
                final_tables[table_name] = out_df_rows

    # delete app names from table names if there is only one app
    if len(apps) == 1:
        for table_name in final_tables.keys():
                if table_name.startswith(apps[0] + '_'):
                    final_tables[table_name.split('_')[-1]] = \
                        final_tables.pop(table_name)


    # --- 5) Optionally store as CSV -------------------------------------------

    if store_as_csv:
        if exp_prefix: exp_prefix += '_'
        for table_name, rows in final_tables.items():
            out_csv = os.path.join(
                data_exp_path, f"{exp_prefix}{table_name}.csv"
            )
            write_dicts_to_csv(rows, out_csv)

    logger.info(f"Normalizing data completed")
    return final_tables
