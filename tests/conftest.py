from utils import *

def pytest_configure(config):
    """
    Delete any stale databases before running tests.
    """
    delete_botex_db()
    delete_otree_db()
    try:
        os.remove("tests/questions_and_answers_local.csv")
        os.remove("tests/questions_and_answers_openai.csv")
        os.remove("tests/botex_participants.csv")
        os.remove("tests/botex_response.csv")
    except OSError:
        pass

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if exitstatus == 0:
        local = config.getoption("--local")
        remote = config.getoption("--remote")
        if not local and not remote:
            local = True
            remote = True
        terminalreporter.ensure_newline()
        if local:
            terminalreporter.section('Local LLM answers', sep='-', blue=True, bold=True)
            terminalreporter.line(create_answer_message("local"))
        if remote:
            terminalreporter.section('OpenAI answers', sep='-', blue=True, bold=True)
            terminalreporter.line(create_answer_message("openai"))


def pytest_addoption(parser):
    parser.addoption("--local", action="store_true", help="Run local LLM workflow tests")
    parser.addoption("--remote", action="store_true", help="Run GPT 4o Remote workflow tests")

def pytest_collection_modifyitems(config, items):
    local = config.getoption("--local")
    remote = config.getoption("--remote")

    if local and remote:
        raise ValueError("Cannot use both --local and --remote flags together")

    selected_items = []
    if local:
        for item in items:
            if any(test in item.nodeid for test in ["test_a_botex_db", "test_b_otree", "test_c_local_llm", "test_d_exports"]):
                selected_items.append(item)
    elif remote:
        for item in items:
            if any(test in item.nodeid for test in ["test_a_botex_db", "test_b_otree", "test_c_openai", "test_d_exports"]):
                selected_items.append(item)
    else:
        selected_items = items  # Default to all tests

    items[:] = selected_items
