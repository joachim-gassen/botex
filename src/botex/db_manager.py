import csv
import json
import logging
import os
from sqlite3 import connect, Connection
from typing import Iterator, Tuple, Any, List, Optional
from threading import Lock
from .local_llm import ChatHistory


class DatabaseManager:
    """
    Manages database operations, specifically for handling data related to participants and conversations within an oTree experiment context.

    :param db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str) -> None:
        """
        Initializes the DatabaseManager with a connection to the specified SQLite database.

        :raises FileNotFoundError: If the directory containing the database file does not exist.
        """
        self.db_path: str = db_path
        db_folder = os.path.dirname(self.db_path)
        if db_folder and not os.path.exists(db_folder):
            raise FileNotFoundError(f"Database folder {db_folder} not found.")
        self.conn: Connection = connect(self.db_path, check_same_thread=False)
        self.lock: Lock = Lock()
        self.setup_botex_db()

    def execute_sql(
        self, sql: str, params: Any = None, many: bool = False, fetch: bool = False
    ) -> Optional[List[Tuple]]:
        """
        Executes SQL commands with optional parameters and returns results if necessary.

        :param sql: SQL statement to execute.
        :param params: Parameters to substitute within the SQL statement.
        :param many: Executes multiple records with 'executemany' if True.
        :param fetch: Fetches records from the database if True.
        :return: List of tuples from fetch operation if fetch is True, otherwise None.
        """
        with self.lock, self.conn as conn:
            cursor = conn.cursor()
            execute_action = cursor.executemany if many else cursor.execute
            execute_action(sql, params) if params else cursor.execute(sql)

            return cursor.fetchall() if fetch else None

    def setup_botex_db(self) -> None:
        """
        Creates necessary tables in the database if they do not already exist.
        """
        self.execute_sql(
            """
            CREATE TABLE IF NOT EXISTS participants (
                session_name VARCHAR,
                session_id CHAR(8),
                participant_id CHAR(8),
                is_human INTEGER,
                url TEXT,
                time_in VARCHAR,
                time_out VARCHAR
            );
        """
        )
        self.execute_sql(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id CHAR(8),
                bot_parms TEXT,
                conversation TEXT
            );
        """
        )

    def get_bot_urls(self, session_id: str) -> List[str]:
        """
        Retrieves the URLs for bots associated with a specific session.

        :param session_id: Identifier of the session.
        :return: List of bot URLs for the session.
        """
        sql = "SELECT url FROM participants WHERE session_id = ? AND is_human = 0"
        rows = self.execute_sql(sql, params=(session_id,), fetch=True)
        return [row[0] for row in rows] if rows else []

    def insert_participants_many(
        self, rows: Iterator[Tuple[str, str, str, bool, str]]
    ) -> None:
        """
        Bulk inserts participant data into the database.

        :param rows: Iterable of tuples containing participant data.
        """
        sql = """
            INSERT INTO participants (
                session_name, session_id, participant_id, is_human, url
            ) VALUES (?, ?, ?, ?, ?)
        """
        self.execute_sql(sql, params=list(rows), many=True)

    def insert_participant(
        self,
        session_name: str,
        session_id: str,
        participant_id: str,
        is_human: int,
        url: str,
        time_in: str,
    ) -> None:
        """
        Inserts a single participant record into the database.

        :param session_name: Name of the session.
        :param session_id: Unique identifier for the session.
        :param participant_id: Unique identifier for the participant.
        :param is_human: Indicates if the participant is human (1) or a bot (0).
        :param url: URL assigned to the participant.
        :param time_in: Timestamp when the participant started the session.
        """
        sql = """
            INSERT INTO participants (
                session_name, session_id, participant_id, is_human, url, time_in
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (session_name, session_id, participant_id, is_human, url, time_in)
        self.execute_sql(sql, params)

    def insert_conversation(
        self, id: str, bot_parms: dict, conversation: ChatHistory
    ) -> None:
        """
        Inserts a conversation record into the database.

        :param id: Identifier of the conversation.
        :param bot_parms: Parameters associated with the bot involved in the conversation.
        :param conversation: History of messages as a ChatHistory object.
        """
        sql = """
            INSERT INTO conversations (id, bot_parms, conversation) 
            VALUES (?, ?, ?)
        """
        params = (id, json.dumps(bot_parms), json.dumps(conversation))
        self.execute_sql(sql, params)

    def update_participant(
        self, session_id: str, participant_id: str, time_out: str
    ) -> None:
        """
        Updates the 'time_out' for a participant record when the session ends.

        :param session_id: Identifier of the session.
        :param participant_id: Identifier of the participant.
        :param time_out: Timestamp when the participant ended the session.
        """
        sql = """
            UPDATE participants SET time_out = ?
            WHERE session_id = ? AND participant_id = ?
        """
        params = (time_out, session_id, participant_id)
        self.execute_sql(sql, params)

    def close(self) -> None:
        """
        Closes the database connection.
        """
        self.conn.close()
