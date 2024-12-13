import argparse
import os
from dotenv import load_dotenv
import logging
import textwrap
import sys


from .otree import get_session_configs, init_otree_session, run_bots_on_session
from .botex_db import export_response_data
from .local_llm import is_llama_cpp_server_reachable
DEFAULT_LLM = 'gemini/gemini-1.5-flash'

def tqs(s):
    # Normalize triple-quoted strings
    s = textwrap.dedent(s)
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    lines = [line.strip() for line in s.split('\n')]
    lines = [line for line in lines if line]
    s = '\n'.join(lines)
    return s

def run_botex():
    parser = argparse.ArgumentParser(
        description=tqs("""
        Run an oTree session with botex. All necessary arguments can be provided 
        either as command line arguments, in the environment file referenced 
        by the '-c' argument, or as environment variables.
        """)
    )
    parser.add_argument(
        '-c', '--config', type=str, default='botex.env',
        help=tqs("""
        Path to the environment file containing the botex configuration.
        Defaults to 'botex.env'.
        """)
    )
    parser.add_argument(
        '-b', '--botex-db', type=str, 
        help=tqs("""
        Path to the botex SQLite database file (will be created if it does 
        not exist). Read from environment variable BOTEX_DB if not provided.
        Defaults to 'botex.db'.
        """)
    )
    parser.add_argument(
        '-u', '--otree-server-url', type=str, 
        help=tqs("""
        oTree server URL. Read from environment variable OTREE_SERVER_URL 
        if not provided. Defaults to 'http://localhost:8000'.
        """)
    )
    parser.add_argument(
        '-r', '--otree-rest-key', nargs='?', default=None, type=str, 
        help=tqs("""
        oTree secret key for its REST API. Read from environment variable
        OTREE_REST_KEY if not provided. Only required if the oTree server
        is running in DEMO or STUDY mode.
        """)
    )
    parser.add_argument(
        '-m', '--model', default=None, type=str,
        help=tqs("""
        Path to the LLM model to use for botex. Read from environment variable 
        LLM_MODEL if not provided. If environment variable is not set, you will be
        prompted for the model.
        """)
    )
    parser.add_argument(
        '-a', '--api-base', default=None, type=str,
        help=tqs("""
        Base URL for the LLM model. If not provided it will default to None for litellm and `http://localhost:8080` for llama.cpp.
        """)
    )
    parser.add_argument(
        '-k', '--api-key', default=None, type=str,
        help=tqs("""
        API key for the LLM model. Read from environment variable API_KEY
        if not provided. If environment variable is not set, you will be
        prompted to enter the key.
        """)
    )
    parser.add_argument(
        '-s', '--session-config', 
        default = None, type=str, 
        help=tqs("""
        oTree session config to run. If not provided, and also not set by the
        environment variable OTREE_SESSION_CONFIG, you will be prompted
        to select from the available session configurations.
        """)
    )
    parser.add_argument(
        '-p', '--nparticipants', type=int,
        help=tqs("""
        Number of participants to run the session with. Read from environment
        variable OTREE_NPARTICIPANTS if not provided.
        """)
    )
    parser.add_argument(
        '-n', '--nhumans', type=int,
        help=tqs("""
        Number of human participants to include in the session with. 
        Read from environment variable OTREE_NHUMANS if not provided.
        Default is 0.
        """)
    )
    parser.add_argument(
        '-e', '--export-csv-file', 
        help = tqs("""
        CSV file to export botex data to. If not provided, you will be prompted
        to enter a file name after the session is complete.
        """)
    )
    parser.add_argument(
        '-x', '--no-throttle', action='store_true',
        help=tqs("""
        Disables throttling requests to deal with rate limiting.
        Defaults to False. If set to True, you might run into rate limiting
        resulting in failed bot runs.
        """)
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Print out botex logs while running. Defaults to False.'
    )
    args = parser.parse_args()

    if os.path.exists(args.config): load_dotenv(args.config)

    otree_server_url = args.otree_server_url
    otree_rest_key = args.otree_rest_key
    session_config = args.session_config
    botex_db = args.botex_db
    model = args.model
    api_key = args.api_key
    api_base = args.api_base
    nparticipants = args.nparticipants
    nhumans = args.nhumans
    throttle = not args.no_throttle
    csv_file = args.export_csv_file
    verbose = args.verbose
    if verbose:
        logging.basicConfig(level=logging.INFO)

    if not otree_server_url:
        otree_server_url = os.getenv('OTREE_SERVER_URL')
    if not otree_rest_key:
        otree_rest_key = os.getenv('OTREE_REST_KEY')
    if not session_config:
        session_config = os.getenv('OTREE_SESSION_CONFIG')

    if not botex_db:
        botex_db = os.getenv('BOTEX_DB')    
    if not model:
        model = os.getenv('LLM_MODEL')
    if not api_key:
        api_key = os.getenv('API_KEY')
    if not nparticipants:
        nparticipants = os.getenv('OTREE_NPARTICIPANTS')
    if not nhumans:
        nhumans = os.getenv('OTREE_NHUMANS')
        if nhumans is None: nhumans = 0
    
    if not botex_db:
        print("Botex database file not provided. Defaulting to 'botex.db'")
        botex_db = 'botex.db'
    if not otree_server_url:
        print("oTree server URL not provided. Defaulting to 'http://localhost:8000'")
        otree_server_url = 'http://localhost:8000'
    
    if not model:
        model = input(tqs(
            f"""
            No LLM provided. Enter your model string here or press enter 
            to accept the default ('{DEFAULT_LLM}'): """
        ))
        if not model: model = DEFAULT_LLM
    if model in ["llama.cpp", "llamacpp"]:
        if not api_base:
            api_base = "http://localhost:8080"
        if is_llama_cpp_server_reachable(api_base):
            print(f"Using LLM model '{model}'")
        else:
            if api_base:
                print(
                    f"The llama.cpp server at {api_base} is not reachable. Are you sure the server is running at this URL? Botex can also start the server for you if you provide the path to the llama server cli in the environment variable PATH_TO_LLAMA_SERVER and the path to the local model in the environment variable LOCAL_LLM_PATH, however, this functionality is not yet implemented in the CLI."
                )
            else:
                print(
                    f"The llama.cpp server at http://localhost:8080 is not reachable. Are you sure the server is running at this URL? If you have started the server at a different URL, provide it with the -a or --api-base argument flag. Botex can also start the server for you if you provide the path to the llama server cli in the environment variable PATH_TO_LLAMA_SERVER and the path to the local model in the environment variable LOCAL_LLM_PATH, however, this functionality is not yet implemented in the CLI."
                )
    else:
        print(f"Using LLM model '{model}'")
        if not api_key:
            api_key = input(tqs("""
            Enter the API key for your LLM model (for the Gemini model, 
            you can get a free API key at https://aistudio.google.com/apikey): 
            """))
        else: 
            print("API key is set")

    try:
        configs = get_session_configs(
            otree_server_url=otree_server_url, 
            otree_rest_key=otree_rest_key
        )    

        if not session_config:
            print("Available session configurations:")
            for i, config in enumerate(configs):
                print(f"{i + 1}: {config['name']}")
            
            choice = int(input("Select a configuration by number: ")) - 1
            session_config = configs[choice]['name']
        else:
            if session_config not in [config['name'] for config in configs]:
                raise ValueError(f"Session configuration '{session_config}' not found")
            
        print("Selected session configuration:", session_config)
            
        config = configs[[config['name'] for config in configs].index(session_config)]

        if not nparticipants:
            if 'num_demo_participants' in config.keys():
                nparticipants = config['num_demo_participants']
            else:
                raise ValueError(tqs(
                    """
                    Number of participants not provided and cannot be inferred
                    from 'num_demo_participants' in the session configuration.
                    """
                ))    

        print("Number of participants:", nparticipants)
        print("Number of human participants:", nhumans)

        session = init_otree_session(
            session_config, nparticipants, nhumans,
            botex_db=botex_db, 
            otree_server_url=otree_server_url, 
            otree_rest_key=otree_rest_key
        )
        session_id = session['session_id']
        print(f"Session '{session_id}' initialized")
        if nhumans > 0:
            print("Human URLs:", session['human_urls'])        
        print(f"You can monitor its progress at {otree_server_url}/SessionMonitor/{session['session_id']}")
        if not throttle and model not in ["llama.cpp", "llamacpp"]:
            print("Throttling is disabled. You might run into rate limiting issues")

        print(f"Starting bots on session...", )
        run_bots_on_session(
            session['session_id'], model=model, api_key=api_key,
            botex_db=botex_db, throttle=throttle
        )
        print (
            "Session complete. You can view the oTree data at",
            f"{otree_server_url}/SessionData/{session['session_id']}"
        )
        print (f"Download the oTree data at: {otree_server_url}/export")
        if not csv_file:
            csv_file = input(
                "Enter CSV file name to export botex data to or press Enter to skip: "
            )
        if csv_file:
            export_response_data(csv_file, botex_db, session['session_id'])

    except Exception as e:
        sys.stderr.write(f"\nError: {e}\n\n")
        parser.print_help(sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    run_botex()