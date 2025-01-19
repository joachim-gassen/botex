# API Reference

This section details the botex API. It consists of a set of Python functions to set up and run oTree-based experiments using LLMs as bots.

The Python API can be divided into two main parts:

1. **oTree Interface**: Functions to interact with the oTree server, such as reading session config data from it, initializing sessions, and running bots on sessions.
2. **Export data**: Functions to export data from the botex database.

## oTree Interface

Running experiments with botex requires an oTree server with an active session to be accessible. The following functions allow the user to interact with the oTree server. Once a session is initialized, the core functions `run_bots_on_session()` and `run_single_bot()` can be used to run bots on the session.

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

## Export botex data

Running oTree experiments with botex generates two databases:

1. The 'normal' experiment data that oTree collects.
2. Additional data that botex collects, such as the prompting sequence between botex and the bots, as well as the answers and the reasoning behind the answers that the LLM bots provide.

botex provides functions to export botex data from the botex database. To obtain oTree data, you need to use the oTree web interface.

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
