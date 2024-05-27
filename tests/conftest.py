import pytest
import yaml
import dotenv
import botex

from tests.utils import *

# Load configuration and environment variables
cfg = yaml.safe_load(open("config.yaml", "r"))
dotenv.load_dotenv("secrets.env")


# Define a fixture for bot_manager
@pytest.fixture(scope="session")
def bot_manager():
    # Create the bot manager object
    manager = botex.LLMOTreeBotsManager(cfg["llm_cfg"], cfg["bot_cfg"])
    return manager


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if exitstatus == 0:
        terminalreporter.ensure_newline()
        terminalreporter.section("Bots answers", sep="-", blue=True, bold=True)
        terminalreporter.line(create_answer_message())
