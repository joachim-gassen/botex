import re
import logging
import json
import time
from datetime import datetime, timezone
import sqlite3
import csv
from importlib.resources import files

from litellm import completion

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .local_llm import LocalLLM

logging.getLogger("LiteLLM").setLevel(logging.WARNING)

def run_bot(
        botex_db, session_id, url, lock, full_conv_history = False,
        model = "gpt-4o", openai_api_key = None,
        local_llm: LocalLLM | None = None
    ):
    """
    Run a bot on an oTree session. Normally, this function should not be called
    directly, but through the run_bots_on_session function.

    Parameters:
    botex_db (str): The name of the SQLite database file to store BotEx data.
    session_id (str): The ID of the oTree session.
    url (str): The participant URL of the bot instance.
    lock (threading.Lock): A lock to prevent concurrent access to the local model.
    full_conv_history (bool): Whether to keep the full conversation history.
        This will increase token use and only work with very short experiments.
        Default is False.
    model (str): The model to use for the bot. Default is "gpt-4-turbo-preview"
        from OpenAI. You will need an OpenAI key and be prepared to pay to 
        use this model.
    openai_api_key (str): The API key for the OpenAI service.
    local_llm (LocalLLM): A LocalLLM object to use for the bot. If this is not
        None, the bot will use the local model instead of the OpenAI model.

    Returns: None (conversation is stored in BotEx database)
    """
    bot_parms = locals()
    bot_parms.pop('lock')
    bot_parms.pop('local_llm')
    bot_parms['local_llm'] = vars(local_llm) if local_llm else None
    if bot_parms['openai_api_key'] is not None: 
        bot_parms["openai_api_key"] = "******"       
    bot_parms = json.dumps(bot_parms)
    logging.info(f"Running bot with parameters: {bot_parms}")

    def click_on_element_by_id(dr, id, timeout = 3600):
        chart = WebDriverWait(dr, timeout).until(
            EC.visibility_of_element_located((By.ID, id))
        )
        dr.execute_script("arguments[0].scrollIntoView(true)", chart)
        element = WebDriverWait(dr, timeout).until(
            EC.element_to_be_clickable((By.ID, id))
        )
        dr.execute_script("arguments[0].click()", element)

    def click_on_element(dr, element, timeout = 3600):
        dr.execute_script("arguments[0].scrollIntoView(true)", element)
        element = WebDriverWait(dr, timeout).until(
            EC.element_to_be_clickable(element)
        )
        dr.execute_script("arguments[0].click()", element)

    def set_id_value(dr, id, type, value, timeout = 3600):
        if type != "radio":
            WebDriverWait(dr, timeout).until(lambda x: x.find_element(By.ID, id)).send_keys(str(value))
        else:
            rb = dr.find_element(By.ID, id)
            resp = rb.find_elements(By.CLASS_NAME, "form-check")
            for r in resp:
                if r.text == value:
                    click_on_element(
                        dr, r.find_element(By.CLASS_NAME, "form-check-input")
                    )
                    break
    
    def wait_next_page(dr, timeout = 10):
        attempts = 0
        while attempts < 600:
            try:
                WebDriverWait(dr, timeout).until(
                    lambda x: x.find_element(By.CLASS_NAME, 'otree-form')
                )
                break # Exit the loop if successful
            except TimeoutException:
                attempts += 1
                continue # Retry if a timeout occurs
        
        if attempts == 600:
            logging.error("Timeout on wait page after 600 attempts.")
            raise Exception("Timeout on wait page after 600 attempts.")

        
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
        question_type = []
        fe = dr.find_elements(By.CLASS_NAME, 'controls')
        for i in range(len(fe)): 
            el = fe[i].find_elements(By.XPATH, ".//*")
            for j in range(len(el)):
                id = el[j].get_attribute("id")
                if id != '': 
                    question_id.append(id)
                    type = el[j].get_attribute("type")
                    if type == 'text':
                        if el[j].get_attribute("inputmode") == 'decimal':
                            type = "float"
                    if type is None:
                        # this is the case when question is a radio button
                        # and potentially also for other non-standard types
                        type = "radio"
                    question_type.append(type)
                    break
        if question_id != []:
            labels = dr.find_elements(By.CLASS_NAME, 'col-form-label')
            question_label = [x.text for x in labels]
            questions = [
                {"question_id": id, "question_type": qtype, "question_label": label} 
                for id, qtype, label in 
                zip(question_id, question_type, question_label, strict = True)
            ]
        else:
            questions =  None
        return (
            text, wait_page, next_button, questions
        )
    
    def llm_send_message(
            message, conv_hist, check_response = None, 
            model = model, nopause = False
        ):
        if not full_conv_history:
            conversation = [
                {
                    "role": "system",
                    "content": prompts['system']
                }
            ]
            if conv_hist == []:
                conv_hist += conversation
        else:
            conversation = conv_hist
        resp_dict = None
        while resp_dict is None:
            conversation.append({"role": "user", "content": message})
            if not full_conv_history:
                conv_hist.append({"role": "user", "content": message})
            if model == "local":
                assert local_llm, "Model is local but local_llm is not set."
                assert conversation, "Conversation is empty."
                with lock:
                    resp = local_llm.completion(conversation)
            else:
                resp =  completion(    
                    messages=conversation, model=model,
                    api_key=openai_api_key,
                    response_format = {"type": "json_object"}
                )

            resp_str = resp.choices[0].message.content
            conv_hist.append({"role": "assistant", "content": resp_str})
            if resp.choices[0].finish_reason == "length":
                logging.warning("Bot's response is too long. Trying again.")
                message = prompts['resp_too_long']
                continue

            try:
                start = resp_str.find('{', 0)
                end = resp_str.rfind('}', start)
                resp_str = resp_str[start:end+1]
                resp_dict = json.loads(resp_str, strict = False)
                if not check_response is None:
                    resp_dict = check_response(resp_dict)
            except:
                logging.exception('')
                logging.warning("Bot's response is not a valid JSON. Trying again.")
                resp_dict = None
                message = prompts['json_error']
                continue
            
            if "error" in resp_dict:
                resp_dict = None
                message = prompts['confused']

        return resp_dict

    def check_response_start(resp):
        if "error" in resp:
            logging.warning(f"Bot's response indicates error: '{resp['error']}'.")
            return resp
        if set(resp) != set(["understood"]):
            raise RuntimeError("Bot's response does not have the required set of keys.")
        if not str(resp['understood']).lower() == "yes":
            raise logging.warning("Bot did not understand the message.")
        return resp

    def check_response_summary(resp):
        if "error" in resp:
            logging.warning(f"Bot's response indicates error: '{resp['error']}'.")
            return resp
        if set(resp) != set(["summary"]):
            raise RuntimeError("Bot's response does not have the required set of keys.")
        return resp

    def check_response_question(resp):
        if "error" in resp:
            logging.warning(f"Bot's response indicates error: '{resp['error']}'.")
            return resp
        keys = ['questions', 'summary']
        if set(resp) != set(keys):
            raise RuntimeError("Bot's response does not have the required set of keys.")
        if not isinstance(resp['questions'], list):
            if isinstance(resp['questions'], dict):
                resp['questions'] = [resp['questions']]
            else: raise RuntimeError("Questions is not a list.")
        for i,q in enumerate(resp['questions']):
            if not isinstance(q, dict):
                raise RuntimeError(f"Question {i} is not a dictionary.")
            if set(q) != set(['id', 'answer', 'reason']):
                raise RuntimeError(f"Question {i} does not have the required set of keys.")
        return resp
            
    def check_response_end(resp):
        if "error" in resp:
            logging.warning(f"Bot's response indicates error: '{resp['error']}'.")
            return resp
        if set(resp) != set(["remarks"]) in resp:
            raise RuntimeError("Bot's response does not have the required set of keys.")
        return resp
    
    conn = sqlite3.connect(botex_db)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE participants SET time_in = ?
        WHERE session_id = ? and url = ?
        """, 
        (datetime.now(timezone.utc).isoformat(), session_id, url)
    )
    conn.commit()
    cursor.close()
    conn.close()


    with open(files('botex').joinpath('bot_prompts.csv'), 'r') as f:
        rv = csv.reader(f)
        next(rv)
        prompts = dict()
        for row in rv: prompts[row[0]] = row[1]

    message = prompts['start']
    conv = []
    resp = llm_send_message(message, conv, check_response_start)
    logging.info(f"Bot's response to start message: '{resp}'")
    
    options = Options()
    options.add_argument("--headless=new")
    # Needed to work on codespaces but might be a security risk on
    # untrusted web pages
    options.add_argument("--no-sandbox")
    attempts = 0
    while attempts < 5:
        try:
            dr = webdriver.Chrome(options = options)
            dr.set_window_size(1920, 1400)
            break
        except:
            attempts += 1
            logging.warning("Could not start Chrome. Trying again.")
            time.sleep(1)
    if attempts == 5:
        logging.error("Could not start Chrome after 5 attempts. Stopping.")
        return    
        
    first_page = True
    summary = None
    text = ""
    while True:
        old_text = text
        text, wait_page, next_button, questions = scan_page(dr)
        if wait_page:
            wait_next_page(dr)
            continue

        if full_conv_history:
            if questions: 
                analyze_prompt = 'analyze_page_q_full_hist'
            else: 
                analyze_prompt = 'analyze_page_no_q_full_hist'
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
            check_response = check_response_summary
        else:
            nr_q = len(questions)
            questions_json = json.dumps(questions)
            check_response = check_response_question

        message = prompts[analyze_prompt].format(
            body = text, summary = summary, nr_q = nr_q,
            questions_json = questions_json
        )

        if first_page:
            first_page = False
            if full_conv_history:
                message = re.sub(
                    'You have now proceeded to the next page\\.', 
                    'You are now on the starting page of the survey/experiment\\.', 
                    message
                )
        
        if old_text == text:
            logging.warning("Bot's answers were likely erroneous. Trying again.")
            if questions == None:
                logging.warning("""
                    This should only happen with pages containing questions.
                    Most likely something is seriously wrong here.
                """)
            message = prompts['page_not_changed'] + message
            
        resp = llm_send_message(message, conv, check_response)
        logging.info(f"Bot analysis of page: '{resp}'")
        if not full_conv_history: summary = resp['summary']
        if questions is None and next_button is not None:
            logging.info("Page has no question but next button. Clicking")
            click_on_element(dr, next_button)
            continue
        
        if questions is None and next_button is None:
            logging.info("Page has no question and no next button. Stopping.")
            break

        logging.info(
            f"Page has {len(questions)} question(s)."
        )
        for q in resp['questions']: 
            logging.info(
                "Bot has answered question " + 
                f"'{q['id']}' with '{q['answer']}'."
            )
            answer = q['answer']
            try:
                qtype = next(qst['question_type'] for qst in questions if qst['question_id'] == q['id'])
            except:
                logging.warning(f"Question '{q['id']}' not found in questions.")
                qtype = None
                break

            if qtype == 'number' and isinstance(answer, str):
                    int_const_pattern = r'[-+]?[0-9]+'
                    rx = re.compile(int_const_pattern, re.VERBOSE)
                    ints = rx.findall(answer)
                    answer = ints[0]
            if qtype == 'float' and isinstance(answer, str):
                numeric_const_pattern = r'[-+]? (?: (?: \d* \. \d+ ) | (?: \d+ \.? ) )(?: [Ee] [+-]? \d+ ) ?'
                rx = re.compile(numeric_const_pattern, re.VERBOSE)
                floats = rx.findall(answer)
                answer = floats[0]
            if qtype == 'radio' and isinstance(answer, bool):
                answer = 'Yes' if answer else 'No'
            set_id_value(dr, q['id'], qtype, answer)

        if qtype is not None: click_on_element(dr, next_button)
    
    dr.close()
    dr.quit()
    message = prompts['end'].format(summary = summary)
    resp = llm_send_message(message, conv, check_response_end)
    logging.info(f"Bot's final remarks about experiment: '{resp}'")
    logging.info("Bot finished.")
        
    conn = sqlite3.connect(botex_db)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO conversations (id, bot_parms, conversation) 
        VALUES (?, ?, ?)
        """, (url[-8:], bot_parms, json.dumps(conv))
    )
    conn.commit()
    cursor.execute(
        """
        UPDATE participants SET time_out = ? 
        WHERE session_id = ? and url = ?
        """, 
        (datetime.now(timezone.utc).isoformat(), session_id, url)
    )
    conn.commit()
    cursor.close()
    conn.close()

