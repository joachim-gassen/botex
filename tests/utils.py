import subprocess
import os
import dotenv
import time
import csv
import signal
import platform

import psutil
import botex

OTREE_STARTUP_WAIT = 3

def delete_botex_db(botex_db = "tests/botex.db"):
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
    if platform.system() == "Windows":
        otree_proc = subprocess.Popen(
            ["otree", "devserver"], cwd="tests/otree",
            stderr=subprocess.PIPE, stdout=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
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
        if platform.system() == "Windows":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            proc.wait()
        else: 
            proc.children()[0].send_signal(signal.SIGKILL)
            otree_proc.kill()
            otree_proc.wait()
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

def create_answer_message(type):
    csv_file = f"tests/questions_and_answers_{type}.csv"
    if not os.path.exists(csv_file):
        return ""
    with open(csv_file) as f:
        quest_answers = list(csv.DictReader(f))
    am = ""
    for qa in quest_answers:
        am += (
            f"Question: {qa['question']}'\n" +  
            f"Answer: '{qa['answer']}'\n" + 
            f"Rationale: '{qa['reason']}'\n\n"
        )
    return am[:-1]



