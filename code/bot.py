import os
import re
import logging
import json
import random
import time
import sqlite3

import pandas as pd
from dotenv import load_dotenv
from litellm import completion
# from openai import OpenAI

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

logging.getLogger("LiteLLM").setLevel(logging.WARNING)

# Do you want a local llama2 model instead of OpenAI?
# Does not seem as if llama2 can produce JSON output reliably
OLLAMA = False

# Do you want to use the full conversation history in 
# prompts (causes prompts to use too many tokens
# for multiround games)
FULL_HISTORY = False

# OpenAI Tier 1 - Currently not used in code
MAX_REQUESTS_PER_MINUTE=500 
MAX_TOKENS_PER_MINUTE=10000

load_dotenv('secrets.env')
BOT_DB_SQLITE = os.environ.get('BOT_DB_SQLITE')
PAUSE_BETWEEN_OPENAI_REQUESTS = 0
STD_PAUSE = 0

def run_bot(url): 
    def find_control_id_by_class(dr, class_name, timeout = 3600):
        return WebDriverWait(dr, timeout).until(lambda x: x.find_element(By.CLASS_NAME, class_name)).get_attribute("id")

    def set_id_value(dr, id, value, timeout = 3600):
        WebDriverWait(dr, timeout).until(lambda x: x.find_element(By.ID, id)).send_keys(str(value))
    
    def wait_for_id(dr, id, timeout = 3600):
        WebDriverWait(dr, timeout).until(lambda x: x.find_element(By.ID, id))

    def click_next(dr):
        dr.find_element(By.CLASS_NAME, 'otree-btn-next').click()

    def wait_and_click_next(dr, timeout = 3600):
        WebDriverWait(dr, timeout).until(lambda x: x.find_element(By.CLASS_NAME, 'otree-btn-next')).click()

    def wait_next_page(dr, timeout = 3600):
        WebDriverWait(dr, timeout).until(lambda x: x.find_element(By.CLASS_NAME, 'otree-btn-next'))
        
    def scan_page(dr):
        dr.get(url)
        text = dr.find_element(By.TAG_NAME, "body").text
        
        wait_page = dr.find_elements(By.CLASS_NAME, 'otree-wait-page__body') != []
        if wait_page:
            return {
                "text": text, "wait_page": wait_page, 
                "next_button": None, "questions": None
            }
        nb = dr.find_elements(By.CLASS_NAME, 'otree-btn-next')
        if len(nb) > 0: next_button = nb[0] 
        else: next_button = None

        # Identify all form fields by id
        question_id = []
        fe = dr.find_elements(By.CLASS_NAME, 'controls')
        for i in range(len(fe)): 
            el = fe[i].find_elements(By.XPATH, ".//*")
            for j in range(len(el)):
                id = el[j].get_attribute("id")
                if id != '': 
                    question_id.append(id)
                    break
        if question_id != []:
            labels = dr.find_elements(By.CLASS_NAME, 'col-form-label')
            question_label = [x.text for x in labels]
            questions = [
                {"question_id": id, "question_label": label} 
                for id, label in 
                zip(question_id, question_label, strict = True)
            ]
        else:
            questions =  None
        return (
            text, wait_page, next_button, questions
        )

    def llm_send_message(message, conv_hist, nopause = False):
        if not FULL_HISTORY:
            conversation = [
                {
                    "role": "system",
                    "content": prompts.loc['system', 'prompt']
                }
            ]
            if conv_hist == []:
                conv_hist += conversation
        else:
            conversation = conv_hist
        resp_dict = None
        while resp_dict is None:
            conversation.append({"role": "user", "content": message})
            if not FULL_HISTORY:
                conv_hist.append({"role": "user", "content": message})
            if OLLAMA:
                resp = completion(
                    model="ollama/llama2", 
                    messages=conversation, 
                    api_base="http://localhost:11434"
                )
            else:
                # Useful models: # gpt-4 gpt-4-turbo-preview gpt-3.5-turbo
                resp =  completion(    
                    messages=conversation, model="gpt-4-turbo-preview"
                )

            resp_str = resp.choices[0].message.content
            conv_hist.append({"role": "assistant", "content": resp_str})
            try:
                resp_dict = json.loads(resp_str)
            except:
                logging.warn("Bot's response is not a JSON. Trying again.")
                message = prompts.loc['json_error', 'prompt']
        if not nopause:
            sleep_secs = random.normalvariate(
                PAUSE_BETWEEN_OPENAI_REQUESTS, STD_PAUSE
            )
            logging.info(f"Sleeping for {sleep_secs} seconds.")
            time.sleep(sleep_secs)

        return resp_dict

    prompts = pd.read_csv("code/bot_prompts.csv")
    prompts.set_index('id', inplace=True)
    message = prompts.loc['start', 'prompt']
    conv = []
    resp = llm_send_message(message, conv)
    logging.info(f"Bot's response to basic task: '{resp}'")
    
    options = Options()
    options.add_argument("--headless=new")
    dr = webdriver.Chrome(options = options)
    dr.set_window_size(1920, 1400)
    first_page = True
    summary = None
    last_page_wait_page = False
    while True:
        text, wait_page, next_button, questions = scan_page(dr)
        if wait_page:
            last_page_wait_page = True
            wait_next_page(dr)
            continue

        if FULL_HISTORY:
            if questions: analyze_prompt = 'analyze_page_q_full_hist'
            else: analyze_prompt = 'analyze_page_full_hist'
        else:
            if first_page:
                if questions: analyze_prompt = 'analyze_first_page_q'
                else: analyze_prompt = 'analyze_first_page_no_q'
            else:    
                if questions: analyze_prompt = 'analyze_page_q'
                else: analyze_prompt = 'analyze_page_no_q'
        if questions == None:
            nr_q = 0
            questions_json = ""
        else:
            nr_q = len(questions)
            questions_json = json.dumps(questions)

        message = prompts.loc[analyze_prompt, 'prompt'].format(
            body = text, summary = summary, nr_q = nr_q,
            questions_json = questions_json
        )

        if first_page:
            first_page = False
            if FULL_HISTORY:
                message = re.sub(
                    'You have now proceeded to the next page\\.', 
                    'You are now on the starting page of the experiment\\.', 
                    message
                )
            
        resp = llm_send_message(message, conv)
        logging.info(f"Bot analysis of page: '{resp}'")
        if not FULL_HISTORY: summary = resp['summary']
        if questions is None and next_button is not None:
            logging.info("Page has no question but next button. Clicking")
            next_button.click()
            continue
        
        if questions is None and next_button is None:
            logging.info("Page has no question and no next button. Stopping.")
            break

        logging.info(
            f"Page has {len(questions)} question(s)."
        )
        for q in resp['questions']: 
            if isinstance(q, list): q = q[0]
            logging.info(
                "Bot has answered question " + 
                f"'{q['id']}' with '{q['answer']}'."
            )
            answer = q['answer']
            set_id_value(dr, q['id'], answer)

        next_button.click()
    

    message = prompts.loc['end', 'prompt']
    resp = llm_send_message(message, conv)
    logging.info(f"Bot's final remarks about experiment: '{resp}'")
    logging.info("Bot finished.")
        
    conn = sqlite3.connect(BOT_DB_SQLITE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (id, conversation) VALUES (?, ?)", 
        (url[-8:], json.dumps(conv))
    )
    conn.commit()
    cursor.close()
    conn.close()

