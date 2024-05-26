import dotenv
import logging
import yaml

from .utils import start_otree, stop_otree

# from tests.utils import start_otree, stop_otree

import botex

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("llm_otree_bot.log"), logging.StreamHandler()],
)


cfg = yaml.safe_load(open("config.yaml", "r"))
cfg["bot_cfg"]["botex_db"] = "tests/botex.db"
dotenv.load_dotenv("secrets.env")


def test_otree_bot_run_bots_on_session():
    bot_manager = botex.LLMOTreeBotsManager(cfg["llm_cfg"], cfg["bot_cfg"])
    otree_proc = start_otree()
    botex_session = bot_manager.init_otree_session(
        config_name="botex_test", num_participants=2
    )

    bot_manager.run_bots_on_session(
        session_id=botex_session["session_id"],
        bot_urls=botex_session["bot_urls"],
    )
    stop_otree(otree_proc)
