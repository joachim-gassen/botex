from utils import *
import glob

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
    except OSError:
        pass

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if exitstatus == 0:
        models = config.getoption("--model")
        terminalreporter.ensure_newline()
        for m in models:
            terminalreporter.section(f"Answers from '{m}'", sep='-', blue=True, bold=True)
            terminalreporter.line(create_answer_message(m))
        terminalreporter.section(f"Answers from llama.cpp", sep='-', blue=True, bold=True)
        terminalreporter.line(create_answer_message("local"))


def pytest_addoption(parser):
    parser.addoption(
        "--model", action="append", 
        default = ["gemini/gemini-1.5-flash"], 
        # Add "ollama/llama3.1" for test of instructor pipeline. Requires ollama to run
        help="Set the model string on which to run tests. You can specify multiple models."
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
        if "test_c_litellm" in item.nodeid:
            parameterized_items.append(item)
    parameterized_items.sort(key=sort_key)
    selected_items.extend(parameterized_items)
    for item in items:
        if any(test in item.nodeid for test in ["test_c_llamacpp", "test_d_exports"]):
            selected_items.append(item)
        
    items[:] = selected_items