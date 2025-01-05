import subprocess
import signal
import platform
import psutil
import time
import os 
import tempfile
import sqlite3
from threading import Thread
from random import shuffle
from itertools import compress
import requests

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


def start_otree_server(
        project_path = None,
        port = None, 
        log_file = None,
        auth_level = None, 
        rest_key = None,
        admin_password = None,
        timeout = 5
    ):
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
        try: 
            data = call_otree_api(
                requests.get, 'otree_version', otree_rest_key=rest_key
            )
        except:
            data = {'error': "No API response"}

        if 'version' in data:
            logging.info(
                "oTree server started successfully "
                f"with endpoint '{otree_server_url}'"
            )
            break
        else:
            if time.time() > time_out:
                logging.error(
                    f"oTree endpoint '{otree_server_url}' did not respond "
                    f"within {timeout} seconds. Exiting."
                )
                raise Exception('oTree server did not start.')
            time.sleep(1)
    return otree_server


def stop_otree_server(otree_server):
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
    else:
        logging.warning('oTree server already stopped.')
    return otree_server.poll()

 
def get_session_configs(otree_server_url = None, otree_rest_key = None):
    """
    Get the session configurations from an oTree server.

    Parameters:
    otree_server_url (str): The URL of the oTree server. Read from environment
        variable OTREE_SERVER_URL if None (the default).
    otree_rest_key (str): The API key for the oTree server. Read from environment
        variable OTREE_REST_KEY if None (the default).

    Returns:
    list: The session configurations.
    """

    return call_otree_api(
        requests.get, 'session_configs', 
        otree_server_url=otree_server_url, otree_rest_key=otree_rest_key
    )

def init_otree_session(
        config_name, npart, nhumans = 0, 
        is_human = None,
        room_name = None,
        botex_db = None,
        otree_server_url = None,
        otree_rest_key = None,
        modified_session_config_fields = None,
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
    modified_session_config_fields (dict): A dictionary of fields to modify in the
        the oTree session config. Default is None. 

    Returns:
    dict with the keys 'session_id', 'participant_code', 'is_human', 
    'bot_urls', and 'human_urls'
    containing the session ID, participant codes, human indicators,
    and the URLs for the human and bot participants.
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
        session_id, bot_urls = None, 
        botex_db = None, 
        model: str = "gpt-4o-2024-08-06",
        api_key = None,
        api_base: str | None = None,
        throttle = False,
        full_conv_history = False,
        user_prompts: dict | None = None,
        already_started = False,
        wait = True,
        **kwargs
    ):
    """
    Run botex bots on an oTree session.

    Parameters:
    session_id (str): The ID of the oTree session.
    bots_urls (list): A list of URLs for the bot participants.
        Will be retrieved from the database if None (the default).
    botex_db (str): The name of the SQLite database file for BotEx data.
        If None (the default), it will be obtained from the environment 
        variable BOTEX_DB.
    model (str): The model to use for the bot. Default is "gpt-4o-2024-08-06"
        from OpenAI vie LiteLLM. It needs to be a model that supports structured 
        outputs. For OpenAI, these are gpt-4o-mini-2024-07-18 and later or 
        gpt-4o-2024-08-06 and later. If you use a commercial model, You need to
        provide an API key in the parameter 'api_key' and be 
        prepared to pay to use this model. If you want to use local models, 
        we suggest that you use llama.cpp, In this case, set this string
        to "lamacpp" and set the URL of your llama.cpp server in
        'api_base'. If you want botex to start the llama.cpp server for you,
        run 'start_llamacpp_sever()' prior to running
        run_bots_on_session().
    api_key (str): The API key for the model that you use. If None 
        (the default), it will be obtained from environment variables 
        by liteLLM (e.g., OPENAI_API_KEY or GEMINI_API_KEY). 
    api_base (str): The base URL for the llm server. Default is None not to
        interfere with the default LiteLLM behavior. If you want to use a local 
        model with llama.cpp and if you have not explicitly set this parameter, 
        it will default to `http://localhost:8080`, the default url for the
        llama.cpp server.
    throttle (bool): Whether to slow down the bot's requests.
        Slowing done the requests can help to avoid rate limiting. Default is 
        False. The bot will switch to 'throttle=True' when LiteLLM is used and 
        completion requests raise exceptions.
    full_conv_history (bool): Whether to keep the full conversation history.
        This will increase token use and only work with very short experiments.
        Default is False.
    user_prompts (dict): A dictionary of user prompts to override the default 
        prompts that the bot uses. The keys should be one or more of the 
        following: ['start', 'analyze_first_page_no_q', 'analyze_first_page_q', 
        'analyze_page_no_q', 'analyze_page_q', 'analyze_page_no_q_full_hist', 
        'analyze_page_q_full_hist', 'page_not_changed', 'system', 
        'system_full_hist', 'resp_too_long', 'json_error', 'end', 
        'end_full_hist']. If a key is not present in the dictionary, the default 
        prompt will be used. If a key that is not in the default prompts is 
        present in the dictionary, then the bot will exit with a warning and 
        not run to make sure that the user is aware of the issue.
    already_started (bool): If True, the function will also run bots that have
        already started but not yet finished. This is useful if bots did not 
        startup properly because of network issues. Default is False.
    wait (bool): If True (the default), the function will wait for the bots to 
        finish.
    kwargs (dict): Additional keyword arguments to pass on to 
        litellm.completion().
        
    Returns: None (bot conversation logs are stored in database) if wait is True.
        A list of Threads running the bots if wait is False.

    Notes:

        -   When running local models via llama.cpp, if you would like 
            botex to start the llama.cpp server for you, 
            run `start_llamacpp_server()` to start up the server prior to
            running `run_bots_on_session().

    Example Usage:
        # Running botex with the default model ("gpt-4o-2024-08-06")
        run_bots_on_session(
            session_id="your_session_id",
            botex_db="path/to/botex.db",
            api_key="your_openai_api_key",
            # Other parameters if and as needed
        )

        # Using a specific model supported by LiteLLM
        run_bots_on_session(
            session_id="your_session_id",
            botex_db="path/to/botex.db",
            model="gemini/gemini-1.5-flash",
            api_key="your_gemini_api_key",
            # Other parameters if and as needed
        )

        # Using a local model with BotEx starting the llama.cpp server
        llamacpp_config = {
            "server_path": "/path/to/llama/server",
            "local_llm_path": "/path/to/local/model",
            # Additional configuration parameters if and as needed
        }
        process_id = start_llamacpp_server(llamacpp_config)
        run_bots_on_session(
            session_id="your_session_id",
            botex_db="path/to/botex.db",
            model="llamacpp",
            # Other parameters if and as needed
        )
        stop_llamacpp_server(process_id)

        # Using a local model with an already running llama.cpp server
        # that uses an URL different from the default (if you are using
        # the default http://localhost:8080", you can simply omit the
        # `api_base` parameter)
        run_bots_on_session(
            session_id="your_session_id",
            botex_db="path/to/botex.db",
            model = "llamacpp",
            api_base = http://yourserver:port"},
            # Other parameters if and as needed
        )

    """
    if botex_db is None: botex_db = os.environ.get('BOTEX_DB')
    if api_key is None and 'openai_api_key' in kwargs: 
        api_key = kwargs.pop('openai_api_key')
    if bot_urls is None: 
        bot_urls = get_bot_urls(session_id, botex_db, already_started)
    
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
    url,
    session_name = "unknown",
    session_id = "unknown", 
    participant_id = "unknown",
    botex_db = None,
    model: str = "gpt-4o-2024-08-06",
    api_key = None,
    api_base: str | None = None,
    throttle = False, 
    full_conv_history = False,
    user_prompts: dict | None = None,
    wait = True,
    **kwargs
):
    """
    Runs a single botex bot manually.

    Parameters:
    url (str): The participant URL to start the bot on.
    session_name (str): The name of the oTree session. Defaults to "unknown"
    session_id (str): The oTree ID of the oTree session. Defaults to "unknown".
    participant_id (str): The oTree ID of the participant. Defaults to "unknown".
    botex_db (str): The name of the SQLite database file to store botex data.
    full_conv_history (bool): Whether to keep the full conversation history.
        This will increase token use and only work with very short experiments.
        Default is False.
    model (str): The model to use for the bot. Default is "gpt-4o-2024-08-06"
        from OpenAI vie LiteLLM. It needs to be a model that supports structured 
        outputs. For OpenAI, these are gpt-4o-mini-2024-07-18 and later or 
        gpt-4o-2024-08-06 and later. If you use a commercial model, You need to
        provide an API key in the parameter 'api_key' and be 
        prepared to pay to use this model. If you want to use local models, 
        we suggest that you use llama.cpp, In this case, set this string
        to "lamacpp" and set the URL of your llama.cpp server in
        'api_base'. If you want botex to start the llama.cpp server for you,
        run 'start_llamacpp_sever()' prior to running
        run_single_bot().
    api_key (str): The API key for the model that you use. If None 
        (the default), it will be obtained from environment variables 
        by liteLLM (e.g., OPENAI_API_KEY or GEMINI_API_KEY). 
    api_base (str): The base URL for the llm server. Default is None not to
        interfere with the default LiteLLM behavior. If you want to use a local 
        model with llama.cpp and if you have not explicitly set this parameter, 
        it will default to `http://localhost:8080`, the default url for the
        llama.cpp server.
    throttle (bool): Whether to slow down the bot's requests.
        Slowing done the requests can help to avoid rate limiting. Default is 
        False. The bot will switch to 'throttle=True' when LiteLLM is used and 
        completion requests raise exceptions.
    user_prompts (dict): A dictionary of user prompts to override the default 
        prompts that the bot uses. The keys should be one or more of the 
        following: ['start', 'analyze_first_page_no_q', 'analyze_first_page_q', 
        'analyze_page_no_q', 'analyze_page_q', 'analyze_page_no_q_full_hist', 
        'analyze_page_q_full_hist', 'page_not_changed', 'system', 
        'system_full_hist', 'resp_too_long', 'json_error', 'end', 
        'end_full_hist']. If a key is not present in the dictionary, the default 
        prompt will be used. If a key that is not in the default prompts is 
        present in the dictionary, then the bot will exit with a warning and 
        not run to make sure that the user is aware of the issue.
    wait (bool): If True (the default), the function will wait for the bots to 
        finish.
    kwargs (dict): Additional keyword arguments to pass on to 
        litellm.completion().
    
    Returns: None (conversation is stored in the botex database) if wait is True.
        The Thread running the bot if wait is False.

    Notes:

    -   When running local models via llama.cpp, if you would like 
        botex to start the llama.cpp server for you, 
        run `start_llamacpp_server()` to start up the server prior to
        running `run_bots_on_session().
    
    Example Usage:

    # Using a model via LiteLLM
    run_single_bot(
        url="your_participant_url",
        session_name="your_session_name",
        session_id="your_session_id",
        participant_id="your_participant_id",
        botex_db="path/to/botex.db",
        model="a LiteLLM model string, e.g. 'gemini/gemini-1.5-flash'",
        api_key="the API key for your model provide",
        # Other parameters if and as needed
    )


    # Using a local model with an already running llama.cpp server
    # If you want botex to start the llama.cpp server, you need
    # to run `start_llamacpp_server()` prior to running this.
    run_single_bot(
        url="your_participant_url",
        session_name="your_session_name",
        session_id="your_session_id",
        participant_id="your_participant_id",
        botex_db="path/to/botex.db",
        model="llamacpp",
        api_base="http://yourhost:port" # defaults to http://localhost:8080
        # Other parameters if and as needed
    )
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
        csv_file, server_url = None, 
        admin_name = "admin", 
        admin_password = None, time_out = 10
    ):
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
    with tempfile.TemporaryDirectory() as tmp_dir:
        prefs = {"download.default_directory": tmp_dir}
        chrome_options.add_experimental_option("prefs", prefs)
        driver = webdriver.Chrome(options=chrome_options)
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
        download_link.click()

        time_out = time.time() + time_out
        while True:            
            time.sleep(1)
            csv_files = [f for f in os.listdir(tmp_dir) if f.endswith(".csv")]
            if len(csv_files) == 1:
                os.rename(f"{tmp_dir}/{csv_files[0]}", csv_file)
                logging.info("oTree CSV file downloaded.")
                break
            else:
                if time.time() > time_out:
                    logging.error("oTree CSV file download failed.")
                    break
        driver.quit()
