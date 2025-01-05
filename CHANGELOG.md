# Changelog

See https://keepachangelog.com/en/1.0.0/ for a description of the changelog format.

## [Unreleased]

### Added

- Command line interface 'botex'
- Added LLM API throttling to deal with LLM rate limits
- Botex now explicitly checks for oTree validation checks and provides this feedback to LLM bots to trigger corrected responses 
- oTree pages with multiple buttons but no next button are now handled correctly
- Option to use an already existing llama.cpp endpoint
- Parsing of botex environment file by calling 'load_botex_env()'

### Changed

- Communication with LLMs is now based on structured outputs, requiring the use of LLM endpoints that support this feature (making gpt-4o-2024-08-06 the new standard model).
- For those models that don't support structured outputs via LiteLLM, there is a largely untested fallback using the `instructor` package. This is experimental and will likely be removed as soon as LiteLLM supports Ollama's structured output feature.
- Prompting has been improved by streamlining language and adjusting it to the usage of structured outputs.
- The API of the main functions has been standardized and moved closer to the API of LiteLLM.
- `run_bots_on_sesion()` and `run_bot_on_session()` now return the resulting thread object(s) if `wait` is set to `False`.

### Fixed

- Rearranged llama.cpp server logging to a file to avoid pipe buffer overflows.
- Removed deadlock loop on answers that were not accepted by oTree

## [0.1.0] - 2024-07-11

### Added

- Initial release
