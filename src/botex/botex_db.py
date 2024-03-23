import sqlite3
from os import environ


def read_participants_from_botex_db(session_id = None, botex_db = None):
    """
    Read the participants table from the BotEx database.

    Args:
        session_id (str, optional): A session ID to filter the results.
        botex_db (str, optional): The name of a SQLite database file.
        If not provided, it will try to read the file name from
        the environment variable BOTEX_DB.

    Returns:
        List of Dicts: A list of dictionaries with participant data.
    """

    if botex_db is None: botex_db = environ.get('BOTEX_DB')
    conn = sqlite3.connect(botex_db)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    if session_id:
        cursor.execute(
            "SELECT * FROM participants WHERE session_id = ?", (session_id,)
        )
    else:
        cursor.execute("SELECT * FROM participants")
    sessions = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return sessions


def read_conversations_from_botex_db(
        session_id = None, botex_db = None
    ):
    """
    Reads the conversations table from the BotEx database. 
    The conversation table contains the messages exchanged 
    with the LLM underlying the bot.

    Returns:
        List of dicts: A list of dictionaries with the conversation data.
    """
    if botex_db is None: botex_db = environ.get('BOTEX_DB')
    conn = sqlite3.connect(botex_db)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    if session_id:
        cursor.execute(
            "SELECT * FROM conversations WHERE session_id = ?", (session_id,)
        )
    else:
        cursor.execute("SELECT * FROM conversations")
    conversations = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return conversations
