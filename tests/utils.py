import subprocess
import os
import dotenv
import time
import sqlite3

import psutil
import botex

OTREE_STARTUP_WAIT = 3

def delete_botex_db(botex_db = "tests/botex.db"):
    try:
        os.remove(botex_db)
    except OSError:
        pass

def start_otree():
    dotenv.load_dotenv("secrets.env")
    otree_proc = subprocess.Popen(
        ["otree", "devserver"], cwd="tests/otree",
        stderr=subprocess.PIPE, stdout=subprocess.PIPE
    )
    time.sleep(OTREE_STARTUP_WAIT)
    otree_running = otree_proc.poll() is None
    if not otree_running:
        raise Exception(
            "otree devserver failed to start. " + 
            "Maybe an old instance is still running?"
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
    botex_session = botex.init_otree_session(
        config_name="botex_test", npart=2, 
        botex_db = "tests/botex.db",
        otree_server_url="http://localhost:8000"
    )
    return botex_session    


