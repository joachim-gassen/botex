import os
from threading import Thread, Lock
from typing import List

from .db_manager import DatabaseManager
from .message_handler import MessageHandler
from .web_interaction_handler import WebInteractionHandler
from .bot import Bot
from .otree_session_manager import OTreeSessionManager
from .config import LLMConfig, BotConfig


class LLMOTreeBotsManager:
    """
    Orchestrates interactions with an oTree server and manages bots within those sessions.
    This class utilizes configuration for LLM and bot settings to manage sessions and the bots that participate in them.

    :param llm_cfg: Configuration for the language model operations.
    :param bot_cfg: Configuration settings related to bot operations and environment.
    """

    def __init__(
        self,
        llm_cfg: LLMConfig,
        bot_cfg: BotConfig,
    ):
        """
        Initializes the LLMOTreeBotsManager with the necessary configurations.

        :param llm_cfg: Configuration parameters for the language model.
        :param bot_cfg: Bot specific configurations such as database connections and session details.
        """
        self.message_handler = MessageHandler(
            llm_cfg, bot_cfg["prompts"], bot_cfg["full_conv_history"]
        )
        self.web_interaction_handler = WebInteractionHandler()

        self.botex_db = bot_cfg.get("botex_db", os.getenv("BOT_DB_SQLITE"))
        assert self.botex_db, "botex_db must be provided."
        self.db_manager = DatabaseManager(self.botex_db)

        self.otree_session_manager = OTreeSessionManager(
            self.botex_db,
            bot_cfg.get("otree_server_url", os.getenv("OTREE_SERVER_URL")),
            bot_cfg.get("otree_rest_key", os.getenv("OTREE_REST_KEY")),
        )

    def init_otree_session(self, config_name: str, num_participants: int) -> dict:
        """
        Initializes a new session in the oTree system with a specified configuration.

        :param config_name: The name of the session configuration to use.
        :param num_participants: Total number of participants for the session.
        :return: A dictionary containing session details including URLs for bots and humans.
        """
        return self.otree_session_manager.init_otree_session(
            config_name, num_participants
        )

    def run_bots_on_session(
        self, session_id: str, bot_urls: List[str], wait: bool = True
    ):
        """
        Runs multiple bot instances in parallel for a given oTree session.

        :param session_id: The unique identifier for the oTree session.
        :param bot_urls: A list of URLs for each bot to operate on.
        :param wait: Whether to wait for all bots to finish before returning.
        """
        if bot_urls is None:
            bot_urls = self.db_manager.get_bot_urls(session_id)

        lock = Lock()
        threads = [
            Thread(target=self.run_bot, args=(url, session_id, lock))
            for url in bot_urls
        ]

        for t in threads:
            t.start()
        if wait:
            for t in threads:
                t.join()

    def run_bot(self, url: str, session_id: str, lock: Lock):
        """
        Operates a single bot on a given URL using a web driver controlled by the WebInteractionHandler.
        This method ensures each bot operates within a safe thread environment, using a lock for synchronization.

        :param url: The URL for the bot to operate on.
        :param session_id: The session identifier linked to the bot's activity.
        :param lock: A threading lock to ensure thread-safe operations during web interactions.
        """
        assert (
            self.otree_session_manager.otree_server_url
        ), "No otree_server_url provided."
        assert self.otree_session_manager.otree_rest_key, "No otree_rest_key provided."
        bot = Bot(
            session_id,
            self.otree_session_manager.otree_server_url,
            self.otree_session_manager.otree_rest_key,
            self.db_manager,
            self.web_interaction_handler,
            self.message_handler,
        )
        bot.run_bot(url, lock)
