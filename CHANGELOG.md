# Changelog

See https://keepachangelog.com/en/1.0.0/ for a description of the changelog format.

## [Unreleased]

### Added

- Command line interface `botex` to initialize oTree sessions and start bots from the command line
- Added LLM API throttling to deal with LLM rate limits
- botex now explicitly checks for oTree validation checks and provides this feedback to LLM bots to trigger corrected responses 
- oTree pages with multiple buttons but no next button are now handled correctly
- Option to use an already existing llama.cpp endpoint
- Parsing of botex environment file by calling `load_botex_env()` function
- Convenience functions `start_otree_server()` and `stop_otree_server()` to facilitate starting oTree server from within Python
- Function `export_otree_data()` to export oTree wide multi-app data via the oTree web frontend
- Function `normalize_otree_data()` to normalize oTree wide multi-app data to a normalized set of list-of-dicts that is convenient for downstream analysis. This function is based on some educated guesses on the oTree data format and will likely need adjustment for different oTree experiment setups.

### Changed

- Communication with LLMs is now based on structured outputs, requiring the use of LLM endpoints that support this feature (making gpt-4o-2024-08-06 the new standard model).
- For those models that don't support structured outputs via LiteLLM, there is a largely untested fallback using the `instructor` package. This is experimental and will likely be removed as soon as LiteLLM supports Ollama's structured output feature.
- Prompting has been improved by streamlining language and adjusting it to the usage of structured outputs.
- The API of the main functions has been standardized and moved closer to the API of LiteLLM.
- `run_bots_on_session()` and `run_single_bot()` now return the resulting thread object(s) if `wait` is set to `False`.
- botex now logs to its own logger.

### Fixed

- Rearranged llama.cpp server logging to a file to avoid pipe buffer overflows.
- Removed deadlock loop on answers that were not accepted by oTree

## [0.1.0] - 2024-07-11

### Added

- Initial release
