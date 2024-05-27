import logging
import os
from random import shuffle
from typing import List

import requests

from .db_manager import DatabaseManager


class OTreeSessionManager:
    """
    Manages the creation and handling of sessions within the oTree platform.

    :botex_db: The database name for storing experiment data, defaults to environment variable BOTEX_DB.
    :otree_server_url: Base URL of the oTree server, defaults to environment variable OTREE_SERVER_URL.
    :otree_rest_key: REST API key for the oTree server, defaults to environment variable OTREE_REST_KEY.
    """

    def __init__(
        self,
        botex_db: str | None = None,
        otree_server_url: str | None = None,
        otree_rest_key: str | None = None,
    ):
        self.botex_db = botex_db if botex_db else os.getenv("BOTEX_DB")
        self.otree_server_url = (
            otree_server_url if otree_server_url else os.getenv("OTREE_SERVER_URL")
        )
        self.otree_rest_key = (
            otree_rest_key if otree_rest_key else os.getenv("OTREE_REST_KEY")
        )
        assert self.botex_db, "No botex_db provided."
        self.db_manager = DatabaseManager(self.botex_db)
        assert self.otree_server_url, "No otree_server_url provided."
        assert self.otree_rest_key, "No otree_rest_key provided."

    def init_otree_session(
        self,
        config_name: str,
        num_participants: int,
        num_humans: int = 0,
        is_human: List[bool] | None = None,
        room_name: str | None = None,
    ) -> dict:
        """
        Initializes a new session on the oTree platform with specified configuration and participant settings.

        :param config_name: The name of the session configuration to use.
        :param num_participants: Total number of participants for the session.
        :param num_humans: Number of human participants, defaults to 0.
        :param is_human: A list indicating whether each participant is human.
        :param room_name: The name of the room to be used for the session.
        :return: A dictionary containing session details including bot and human URLs.
        :raises ValueError: If `is_human` and `num_humans` are inconsistently provided, or if the lengths do not match `num_participants`.
        """
        assert self.otree_server_url, "No otree_server_url provided."
        assert self.otree_rest_key, "No otree_rest_key provided."

        if num_humans > 0 and is_human is None:
            raise ValueError("Provide either is_human or num_humans, not both.")
        if is_human and len(is_human) != num_participants:
            raise ValueError("Length of is_human must match num_participants.")

        num_bots = num_participants - num_humans
        if is_human is None:
            if num_humans > 0:
                is_human = [True] * num_humans + [False] * (num_bots)
                shuffle(is_human)
            else:
                is_human = [False] * num_participants

        session_id = self.call_api(
            requests.post,
            "sessions",
            session_config_name=config_name,
            num_participants=num_participants,
            room_name=room_name,
        )["code"]
        part_data = sorted(
            self.call_api(requests.get, "sessions", session_id)["participants"],
            key=lambda d: d["id_in_session"],
        )
        part_codes = [p["code"] for p in part_data]

        base_url = self.otree_server_url + "/InitializeParticipant/"
        urls = [base_url + pc for pc in part_codes]

        rows = zip(
            [config_name] * num_participants,
            [session_id] * num_participants,
            part_codes,
            is_human,
            urls,
        )

        self.db_manager.insert_participants_many(rows)

        return {
            "session_id": session_id,
            "participant_code": part_codes,
            "is_human": is_human,
            "bot_urls": [url for url, human in zip(urls, is_human) if not human],
            "human_urls": [url for url, human in zip(urls, is_human) if human],
        }

    def call_api(self, method, *path_parts, **params) -> dict:
        """
        Makes an API call to the oTree server using the provided method, URL path parts, and parameters.

        :param method: The HTTP method (like requests.post or requests.get) to use for the API call.
        :param path_parts: Components of the API endpoint path.
        :param params: Keyword arguments that will be passed as JSON payload to the API.
        :return: The JSON response from the API as a dictionary.
        """
        path_parts = "/".join(path_parts)
        url = f"{self.otree_server_url}/api/{path_parts}"
        resp = method(url, json=params, headers={"otree-rest-key": self.otree_rest_key})
        if not resp.ok:
            logging.error(
                f'Request to "{url}" failed with status {resp.status_code}: {resp.text}'
            )
            raise Exception(f"API Error: {resp.text}")
        return resp.json()
