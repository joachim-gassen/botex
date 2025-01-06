from utils import *
import glob

# DEFAULT_LITELLM_LLM = 'gemini/gemini-1.5-flash'
DEFAULT_LITELLM_LLM = "gpt-4o-2024-08-06"

def pytest_configure(config):
    """
    Delete any stale databases before running tests.
    """
    delete_botex_db()
    delete_otree_db()
    try:
        for f in glob.glob("tests/questions_and_answers_*.csv"):
            os.remove(f)
        os.remove("tests/botex_participants.csv")
        os.remove("tests/botex_response.csv")
        os.remove("tests/otree_data.csv")
        os.remove("tests/otree_data_full_history.csv")
        os.remove("tests/test_participant.csv")
        os.remove("tests/test_session.csv")
        os.remove("tests/test_group.csv")
        os.remove("tests/test_player.csv")
    except OSError:
        pass

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if exitstatus == 0:
        models = config.getoption("--model")
        terminalreporter.ensure_newline()
        for m in models:
            terminalreporter.section(f"Answers from '{m}'", sep='-', blue=True, bold=True)
            terminalreporter.line(create_answer_message(m))


def pytest_addoption(parser):
    parser.addoption(
        "--model", nargs="*",
        default=[DEFAULT_LITELLM_LLM, "llamacpp"],
        help="Set the model string(s) on which to run tests. You can specify multiple models."
    )

def pytest_generate_tests(metafunc):
    if "model" in metafunc.fixturenames:
        metafunc.parametrize("model", metafunc.config.getoption("model"))

def pytest_collection_modifyitems(config, items):
    models = config.getoption("--model")
    def sort_key(item):
        for m in models:
            if m in item.nodeid:
                return models.index(m)
        return len(m)  # Fallback for unmatched items

    selected_items = []
    parameterized_items = []
    for item in items:
        if any(test in item.nodeid for test in ["test_a_botex_db", "test_b_otree"]):
            selected_items.append(item)
    for item in items:
        if "test_c_bots" in item.nodeid: 
            parameterized_items.append(item)
    
    parameterized_items.sort(key=sort_key)
    selected_items.extend(parameterized_items)
    for item in items:
        if any(test in item.nodeid for test in ["test_d_exports"]):
            selected_items.append(item)
        
    items[:] = selected_items
