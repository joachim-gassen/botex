import os
import logging
import textwrap
import sys

import click

from .otree import get_session_configs, otree_server_is_running, \
    start_otree_server, stop_otree_server, init_otree_session, \
    run_bots_on_session
from .botex_db import export_response_data
from .llamacpp import is_llamacpp_server_reachable, start_llamacpp_server, stop_llamacpp_server
from .env import load_botex_env

DEFAULT_LLM = 'gemini/gemini-1.5-flash'


def tqs(s):
    # Normalize triple-quoted strings
    s = textwrap.dedent(s)
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    lines = [line.strip() for line in s.split('\n')]
    lines = [line for line in lines if line]
    s = ' '.join(lines)
    return textwrap.fill(s, width=80) + "\n"

@click.command(help=tqs("""
    Run an oTree session with botex. All necessary arguments can be provided
    either as command line arguments, in the environment file referenced by the
    `-c` argument, or as environment variables.
"""))
@click.option(
    '-c', '--config', type=str, default='botex.env',
    help=tqs("""
        Path to the environment file containing the botex configuration.
        Defaults to 'botex.env'.
    """),
)
@click.option(
    '-i', '--ignore', is_flag=True, default=False,
    help=tqs("""
        Ignore any environment variables and config files.
    """),
)
@click.option(
    '-b', '--botex-db', type=str, 
    help=tqs("""
        Path to the botex SQLite database file (will be created if it does 
        not exist). Read from environment variable BOTEX_DB if not provided.
        Defaults to 'botex.sqlite3'.
    """),
)
@click.option(
    '-u', '--otree-server-url', type=str,
    help=tqs("""
        oTree server URL. Read from environment variable OTREE_SERVER_URL 
        if not provided. Defaults to 'http://localhost:8000'.
    """),
)
@click.option(
    '-r', '--otree-rest-key', default=None, type=str, required=False,
    help=tqs("""
        oTree secret key for its REST API. Read from environment variable
        OTREE_REST_KEY if not provided. Only required if the oTree server
        is running in DEMO or STUDY mode.
    """),
)
@click.option(
    '-m', '--model', default=None, type=str,
    help=tqs("""
        Path to the LLM model to use for botex. Read from environment 
        variable LLM_MODEL if not provided. If environment variable is not 
        set, you will be prompted for the model.
    """),
)
@click.option(
    '-k', '--api-key', default=None, type=str,
    help=tqs("""
        API key for the LLM model. Read from environment variable API_KEY
        if not provided. If environment variable is not set, you will be
        prompted to enter the key.
    """),
)
@click.option(
    '-a', '--api-base', default=None, type=str,
    help=tqs("""
        Base URL for the LLM model. If not provided it will default to None
        for LiteLLM and http://localhost:8080 for llama.cpp.
    """),
)
@click.option(
    '--llamacpp-server', type=str,
    help=tqs("""
        Path to the llama.cpp server executable. Required if the model is
        'llamacpp'. Read from environment variable LLAMACPP_SERVER_PATH
        if not provided.
    """),
)
@click.option(
    '--llamacpp-local-llm', type=str,
    help=tqs("""
        Path to the local llama.cpp model. Required if the model is 
        'llamacpp'. Read from environment variable LLAMACPP_LOCAL_LLM_PATH 
        if not provided.
    """),
)
@click.option(
    '-s', '--session-config', default=None, type=str,
    help=tqs("""
        oTree session config to run. If not provided, and also not set by 
        the environment variable OTREE_SESSION_CONFIG, you will be prompted
        to select from the available session configurations.
    """),
)
@click.option(
    '-p', '--nparticipants', default=None, type=int,
    help=tqs("""
        Number of participants to run the session with. Read from 
        environment variable OTREE_NPARTICIPANTS if not provided.
    """),
)
@click.option(
    '-n', '--nhumans', default=None, type=int,
    help=tqs("""
        Number of human participants to include in the session. 
        Read from environment variable OTREE_NHUMANS if not provided.
    """),
)
@click.option(
    '-e', '--export-csv-file', default=None,
    help=tqs("""
        CSV file to export botex data to. If not provided, you will be
        prompted to enter a file name after the session is complete.
    """),
)
@click.option(
    '-x', '--no-throttle', is_flag=True, default=False,
    help=tqs("""
        Disables throttling requests to deal with rate limiting.
        Defaults to False. If set to True, you might run into rate limiting
        resulting in failed bot runs.
    """),
)
@click.option(
    '-v', '--verbose', is_flag=True, default=False,
    help="Print out botex logs while running. Defaults to False."
)
def run_botex(
    config,
    ignore,
    botex_db,
    otree_server_url,
    otree_rest_key,
    model,
    api_key,
    api_base,
    llamacpp_server,
    llamacpp_local_llm,
    session_config,
    nparticipants,
    nhumans,
    export_csv_file,
    no_throttle,
    verbose
):
    """Main entry-point for running botex with click-based CLI."""
    # Load environment variables from config (if the file exists and ignore is not set)
    if os.path.exists(config) and not ignore:
        click.echo(f"Loading botex config from '{config}'")
        load_botex_env(config)

    # Logging
    if verbose:
        logging.basicConfig(level=logging.INFO)

    # If not ignoring environment variables, pull from environment if not passed in
    if not ignore:
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
        if not api_base:
            api_base = os.getenv('API_BASE')
        if not llamacpp_server:
            llamacpp_server = os.getenv('LLAMACPP_SERVER_PATH')
        if not llamacpp_local_llm:
            llamacpp_local_llm = os.getenv('LLAMACPP_LOCAL_LLM_PATH')
        if not nparticipants:
            env_nparticipants = os.getenv('OTREE_NPARTICIPANTS')
            if env_nparticipants is not None:
                nparticipants = int(env_nparticipants)
        if nhumans is None:
            env_nhumans = os.getenv('OTREE_NHUMANS')
            if env_nhumans is not None:
                nhumans = int(env_nhumans)

    click.echo() 

    # Default fallback for DB
    if not botex_db:
        click.echo(
            "botex database file not provided. Defaulting to 'botex.sqlite3'"
        )
        botex_db = 'botex.sqlite3'

    # Default fallback for oTree server URL
    if not otree_server_url:
        click.echo(
            "oTree server URL not provided. Defaulting to 'http://localhost:8000'"
        )
        otree_server_url = 'http://localhost:8000'

    # Check if oTree server is reachable
    otree_available = otree_server_is_running(
        server_url = otree_server_url, 
        rest_key = otree_rest_key
    )
    if not otree_available:
        click.echo(f"oTree server at '{otree_server_url}' is not reachable.")
        click.echo()
        confirm = click.confirm(
            'Do you want me to start an otree instance?', 
            default=True
        )
        if not confirm:
            click.echo("Exiting...")
            click.echo()
            sys.exit(1)
        else:
            otree_project_path = click.prompt(
                'Enter your oTree project folder', default='otree'
            )
            if otree_rest_key:
                click.echo(
                    f"Starting oTree server at '{otree_server_url}' with "
                    "authentication level 'STUDY'..."
                )
                otree_process = start_otree_server(
                    otree_project_path, port=8000,
                    auth_level='STUDY', rest_key=otree_rest_key
                )
            else:
                click.echo(f"Starting oTree server at '{otree_server_url}'...")
                start_otree_server(otree_project_path)
            
    else:
        click.echo(f"oTree server at '{otree_server_url}' is reachable.")
        otree_process = None

    # If model is not provided, check if llama.cpp is feasible or prompt
    if not model:
        if llamacpp_server and llamacpp_local_llm:
            click.echo(
                "llama.cpp server path and local model path provided. "
                "Defaulting to 'llamacpp'."
            )
            model = "llamacpp"
        else:
            # Prompt user for model
            model_input = click.prompt(
                tqs("""
                    No LLM provided. Enter your model string here 
                    ("llamacpp" if you are using llama.cpp)
                    or press enter to accept the default
                """).strip(),
                default=DEFAULT_LLM,
                type=str
            )
            model = model_input if model_input else DEFAULT_LLM

    # Handle llama.cpp
    if model == "llamacpp":
        llamacpp_process = None
        if not api_base:
            api_base = "http://localhost:8080"

        # Check if server is already reachable
        if is_llamacpp_server_reachable(api_base):
            click.echo(f"llama.cpp server is reachable at '{api_base}'")
        else:
            # Attempt to start server if possible
            if llamacpp_server and llamacpp_local_llm:
                llamacpp_process = start_llamacpp_server({
                    "server_path": llamacpp_server,
                    "local_llm_path": llamacpp_local_llm
                })
                if llamacpp_process:
                    click.echo("llama.cpp server started successfully.")
                else:
                    click.echo("Failed to start llama.cpp server.")
                    sys.exit(1)
            else:
                click.echo("")
                click.echo(tqs(
                    f"""
                    The llama.cpp server at {api_base} is not reachable. 
                    Are you sure the server is reachable at this URL? 
                    botex can also start the server for you if you 
                    provide the path to the llama.cpp server and the 
                    path to the local model either as command line 
                    arguments, in the config file, or as environment 
                    variables.
                    """
                ))
                sys.exit(1)
    else:
        click.echo(f"Using LiteLLM with model '{model}'")
        if not api_key:
            # Prompt user for API key
            api_key = click.prompt(
                tqs("""
                    Enter the API key for your LLM model (for the Gemini model, 
                    you can get a free API key at
                    https://aistudio.google.com/apikey)
                """).strip(), type=str
            )
        else:
            click.echo("API key is set")

    # Retrieve the list of session configs
    configs = get_session_configs(
        otree_server_url=otree_server_url, 
        otree_rest_key=otree_rest_key
    )

    # If session_config not provided, prompt user
    if not session_config:
        click.echo("\nAvailable session configurations:")
        for i, conf in enumerate(configs):
            click.echo(f"{i + 1}: {conf['name']}")
        choice = click.prompt(
            "Select a configuration by number", type=int
        ) - 1
        session_config = configs[choice]['name']
    else:
        # Validate session_config
        config_names = [conf['name'] for conf in configs]
        if session_config not in config_names:
            raise ValueError(f"Session configuration '{session_config}' not found")

    # Print user choice
    click.echo(f"\nSelected session configuration: {session_config}")
    chosen_config = next(conf for conf in configs if conf['name'] == session_config)

    # If participants not specified, try to use config's num_demo_participants
    if not nparticipants:
        if 'num_demo_participants' in chosen_config:
            nparticipants = chosen_config['num_demo_participants']
        else:
            raise ValueError(tqs(
                """
                Number of participants not provided and cannot be inferred
                from 'num_demo_participants' in the session configuration.
                """
            ))
        
    # If nhumans was never set, prompt for it
    if nhumans is None:
        nhumans = click.prompt(
            "Enter number of human participants", default=0, type=int
        )

    click.echo(f"Number of participants: {nparticipants}")
    click.echo(f"Number of human participants: {nhumans}")

    session = init_otree_session(
        session_config,
        nparticipants,
        nhumans,
        botex_db=botex_db,
        otree_server_url=otree_server_url,
        otree_rest_key=otree_rest_key
    )
    session_id = session['session_id']
    click.echo(f"Session '{session_id}' initialized")

    if nhumans > 0:
        click.echo(f"Human URLs: {session['human_urls']}")
    click.echo(
        f"You can monitor its progress at "
        f"{otree_server_url}/SessionMonitor/{session_id}"
    )

    # Throttling notice
    throttle = not no_throttle
    if not throttle and model not in ["llama.cpp", "llamacpp"]:
        click.echo("Throttling is disabled. You might run into rate limiting issues")

    click.echo("Starting bots on session...")
    run_bots_on_session(
        session_id,
        model=model,
        api_key=api_key,
        botex_db=botex_db,
        throttle=throttle
    )

    # If we launched a llama.cpp process, shut it down
    if model == "llamacpp" and 'llamacpp_process' in locals() and llamacpp_process:
        click.echo("Stopping llama.cpp server...")
        stop_llamacpp_server(llamacpp_process)

    click.echo("\nSession complete.")
    click.echo(
        f"You can view the oTree data at "
        f"{otree_server_url}/SessionData/{session_id}"
    )
    click.echo(f"Download the oTree data at: {otree_server_url}/export")

    # Possibly prompt user for a CSV file name
    csv_file = export_csv_file
    if not csv_file:
        csv_file = click.prompt(
            "Enter CSV file name to export botex data to or press Enter to skip",
            default="",
            show_default=False
        )
        if not csv_file.strip():
            csv_file = None

    if csv_file:
        export_response_data(csv_file, botex_db, session_id)
    
    if otree_process:
        confirm = click.confirm(
            "Do you want me to stop the oTree server?", default=True
        ) 
        if confirm:
            stop_otree_server(otree_process)
            click.echo("oTree server stopped.")


if __name__ == "__main__":
    # Entry point for the Click command
    run_botex()
