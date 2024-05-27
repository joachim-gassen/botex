import subprocess
import os
import dotenv
import time
import csv

import psutil
import botex

OTREE_STARTUP_WAIT = 3


def delete_botex_db(botex_db="tests/botex.db"):
    try:
        os.remove(botex_db)
    except OSError:
        pass


def delete_otree_db():
    try:
        os.remove("tests/otree/db.sqlite3")
    except OSError:
        pass


def start_otree():
    dotenv.load_dotenv("secrets.env")
    otree_proc = subprocess.Popen(
        ["otree", "devserver"],
        cwd="tests/otree",
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    time.sleep(OTREE_STARTUP_WAIT)
    otree_running = otree_proc.poll() is None
    if not otree_running:
        raise Exception(
            "otree devserver failed to start. "
            + "Maybe an old instance is still running?"
        )
    return otree_proc


def stop_otree(otree_proc):
    otree_running = otree_proc.poll() is None
    if otree_running:
        proc = psutil.Process(otree_proc.pid)
        proc.children()[0].send_signal(9)
        otree_proc.kill()
    try:
        os.remove("tests/otree/db.sqlite3")
    except OSError:
        pass


def init_otree_test_session():

    otree_session_manager = botex.OTreeSessionManager(
        botex_db="tests/botex.db",
        otree_server_url="http://localhost:8000",
    )
    botex_session = otree_session_manager.init_otree_session(
        config_name="botex_test", num_participants=2
    )

    return botex_session


def create_answer_message():
    if not os.path.exists("tests/questions_and_answers.csv"):
        return ""
    with open("tests/questions_and_answers.csv") as f:
        quest_answers = list(csv.DictReader(f))
    am = ""
    for qa in quest_answers:
        am += (
            f"Question: {qa['question']}'\n"
            + f"Answer: '{qa['answer']}'\n"
            + f"Rationale: '{qa['reason']}'.\n\n"
        )
    return am[:-1]
