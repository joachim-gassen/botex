from utils import *

def pytest_configure(config):
    """
    Delete any stale databases before running tests.
    """
    delete_botex_db()
    delete_otree_db()
    try:
        os.remove("tests/questions_and_answers.csv")
        os.remove("tests/botex_participants.csv")
        os.remove("tests/botex_response.csv")
    except OSError:
        pass

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if exitstatus == 0:
        terminalreporter.ensure_newline()
        terminalreporter.section('Bots answers', sep='-', blue=True, bold=True)
        terminalreporter.line(create_answer_message())