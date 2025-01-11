# API Reference

This section details the botex API. It consists of the command line interface  `botex` and a set of Python functions to set up and run oTree-based experiments using LLMs as bots.

The Python API can be divided into three main parts:

1. **Setup**: Functions to set up the botex configuration and to start/stop a local llama.cpp server if needed.
2. **oTree Interface**: Functions to interact with the oTree server, such as starting/stopping the server, reading session config data from it, initializing sessions, and running bots on sessions.
3. **Export data**: Functions to export data from the botex and oTree databases.

## Command Line Interface

The `botex` command line interface provides the option to set up and run oTree experiments with bots from the command line. It also allows the user to export data from both, the botex and the oTree databases.

::: mkdocs-click
    :module: botex.cli
    :command: run_botex
    :prog_name: botex
    :depth: 1

## Python API: Setup

The botex configuration can be provided via function parameters or by setting environment variables. The latter is useful for secrets like API keys and also makes handling the API easier if you run repeated experiments. This an be facilitated by calling the function `load_botex_env()` that reads an `.env` file (`botex.env` by default). For users that want to use local LLMs for inference, `botex`can also start and/or stop a local llama.cpp instance.

### `load_botex_env`
::: botex.env.load_botex_env
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `start_llamacpp_server`
::: botex.llamacpp.start_llamacpp_server
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `stop_llamacpp_server`
::: botex.llamacpp.stop_llamacpp_server
    options:
      show_root_heading: false
      show_root_toc_entry: false

## Python API: oTree Interface

Running experiments with botex requires an oTree server with an active session to be accessible. The following functions allow the user to interact with the oTree server, such as starting/stopping the server, reading session config data from it, and initializing sessions. Once a session is initialized, the core functions `run_bots_on_session()` and `run_single_bot()` can be used to run bots on the session.

### `start_otree_server`
::: botex.otree.start_otree_server
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `stop_otree_server`
::: botex.otree.stop_otree_server
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `get_session_configs`
::: botex.otree.get_session_configs
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `init_otree_session`
::: botex.otree.init_otree_session
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `get_bot_urls`
::: botex.otree.get_bot_urls
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `run_bots_on_session`
::: botex.otree.run_bots_on_session
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `run_single_bot`
::: botex.otree.run_single_bot
    options:
      show_root_heading: false
      show_root_toc_entry: false

## Python API: Export data

Running oTree experiments with botex generates two data sources:

1. The 'normal' experiment data that oTree collects.
2. Additional data that botex collects, such as the prompting sequence between botex and the bots, as well as the answers and the reasoning behind the answers that the LLM bots provide.

botex provides functions to export these data from the botex and oTree databases. In addition, the function `normalize_otree_data()` can be used to re-organize the wide multi-app oTree data into a normalized format that is more convenient for downstream use.

### `read_participants_from_botex_db`
::: botex.botex_db.read_participants_from_botex_db
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `read_conversations_from_botex_db`
::: botex.botex_db.read_conversations_from_botex_db
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `read_responses_from_botex_db`
::: botex.botex_db.read_responses_from_botex_db
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `export_participant_data`
::: botex.botex_db.export_participant_data
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `export_response_data`
::: botex.botex_db.export_response_data
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `export_otree_data`
::: botex.otree.export_otree_data
    options:
      show_root_heading: false
      show_root_toc_entry: false

### `normalize_otree_data`
::: botex.otree.normalize_otree_data
    options:
      show_root_heading: false
      show_root_toc_entry: false