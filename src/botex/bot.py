import re
import logging
import json
from datetime import datetime, timezone
import sqlite3
import csv
from importlib.resources import files

from litellm import completion

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

logging.getLogger("LiteLLM").setLevel(logging.WARNING)

def run_bot(
        botex_db, session_id, url, full_conv_history = False,
        model = "gpt-4-turbo-preview", openai_api_key = None,
        api_base = "http://localhost:11434"
    ): 
    """
    Run a bot on an oTree session. Normally, this function should not be called
    directly, but through the run_bots_on_session function.

    Parameters:
    botex_db (str): The name of the SQLite database file to store BotEx data.
    session_id (str): The ID of the oTree session.
    url (str): The participant URL of the bot instance.
    full_conv_history (bool): Whether to keep the full conversation history.
        This will increase token use and only work with very short experiments.
        Default is False.
    model (str): The model to use for the bot. Default is "gpt-4-turbo-preview"
        from OpenAI. You will need an OpenAI key and be prepared to pay to 
        use this model.
    openai_api_key (str): The API key for the OpenAI service.
    api_base (str): The base URL for the LiteLLM service. Default is
        "http://localhost:11434", assuming that you are running an Ollama 
        service. Currently, models other than OpenAI GPT-4 are untested and
        very likely to fail.

    Returns: None (conversation is stored in BotEx database)
    """        
    bot_parms = json.dumps(locals())
    logging.info(f"Running bot with parameters: {bot_parms}")

    def set_id_value(dr, id, type, value, timeout = 3600):
        if type != "radio":
            WebDriverWait(dr, timeout).until(lambda x: x.find_element(By.ID, id)).send_keys(str(value))
        else:
            rb = dr.find_element(By.ID, id)
            resp = rb.find_elements(By.CLASS_NAME, "form-check")
            for r in resp:
                if r.text == value:
                    r.find_element(By.CLASS_NAME, "form-check-input").click()
                    break
    
    def wait_next_page(dr, timeout = 3600):
        WebDriverWait(dr, timeout).until(lambda x: x.find_element(By.CLASS_NAME, 'otree-form'))
        
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
            if model == "ollama/llama2":
                resp = completion(
                    model=model, 
                    messages=conversation, 
                    api_base=api_base
                )
            else:
                resp =  completion(    
                    messages=conversation, model=model,
                    api_key=openai_api_key
                )

            resp_str = resp.choices[0].message.content
            conv_hist.append({"role": "assistant", "content": resp_str})
            if resp.choices[0].finish_reason == "length":
                logging.warn("Bot's response is too long. Trying again.")
                message = prompts['resp_too_long']
                continue

            try:
                start = resp_str.find('{', 0)
                end = resp_str.rfind('}', start)
                resp_str = resp_str[start:end+1]
                resp_dict = json.loads(resp_str)
                if not check_response is None:
                    resp_dict = check_response(resp_dict)
            except:
                logging.warn("Bot's response is not a JSON. Trying again.")
                message = prompts['json_error']
                continue
            
            if "error" in resp_dict:
                resp_dict = None
                message = prompts['confused']

        return resp_dict

    def check_response_start(resp):
        if "error" in resp:
            logging.warn(f"Bot's response indicates error: '{resp['error']}'.")
            return resp
        if not "understood" in resp:
            raise RuntimeError("Bot's response does not contain the 'understood' key.")
        if not str(resp['understood']).lower() == "yes":
            raise logging.warn("Bot did not understand the message.")
        return resp

    def check_response_summary(resp):
        if "error" in resp:
            logging.warn(f"Bot's response indicates error: '{resp['error']}'.")
            return resp
        if not "summary" in resp:
            raise RuntimeError("Bot's response does not contain the 'summary' key.")
        return resp

    def check_response_question(resp):
        if "error" in resp:
            logging.warn(f"Bot's response indicates error: '{resp['error']}'.")
            return resp
        keys = ['questions', 'summary']
        if not all(k in resp for k in keys):
            raise RuntimeError("Bot's response does not contain all required keys.")
        if not isinstance(resp['questions'], list):
            if isinstance(resp['questions'], dict):
                resp['questions'] = [resp['questions']]
            raise RuntimeError("Questions is not a list.")
        for i,q in enumerate(resp['questions']):
            if not isinstance(q, dict):
                raise RuntimeError(f"Question {i} is not a dictionary.")
            if not all(k in q for k in ['id', 'answer', 'reason']):
                raise RuntimeError(f"Question {i} does not contain all required keys.")
        return resp
            
    def check_response_end(resp):
        if "error" in resp:
            logging.warn(f"Bot's response indicates error: '{resp['error']}'.")
            return resp
        if not "remarks" in resp:
            raise RuntimeError("Bot's response does not contain the 'remarks' key.")
        return resp
    
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
    dr = webdriver.Chrome(options = options)
    dr.set_window_size(1920, 1400)
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
                    'You are now on the starting page of the experiment\\.', 
                    message
                )
        
        if old_text == text:
            logging.warn("Bot's answers were likely erroneous. Trying again.")
            if questions == None:
                logging.warn("""
                    This should only happen with pages containing questions.
                    Most likely something is seriously wrong here.
                """)
            message = prompts['page_not_changed'] + message
            
        resp = llm_send_message(message, conv, check_response)
        logging.info(f"Bot analysis of page: '{resp}'")
        if not full_conv_history: summary = resp['summary']
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
            logging.info(
                "Bot has answered question " + 
                f"'{q['id']}' with '{q['answer']}'."
            )
            answer = q['answer']
            qtype = next(qst['question_type'] for qst in questions if qst['question_id'] == q['id'])
            if qtype == 'number' and isinstance(answer, str):
                    int_const_pattern = '[-+]?[0-9]+'
                    rx = re.compile(int_const_pattern, re.VERBOSE)
                    ints = rx.findall(answer)
                    answer = ints[0]
            if qtype == 'float' and isinstance(answer, str):
                numeric_const_pattern = '[-+]? (?: (?: \d* \. \d+ ) | (?: \d+ \.? ) )(?: [Ee] [+-]? \d+ ) ?'
                rx = re.compile(numeric_const_pattern, re.VERBOSE)
                floats = rx.findall(answer)
                answer = floats[0]
            set_id_value(dr, q['id'], qtype, answer)

        next_button.click()
    
    message = prompts['end']
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
        (datetime.now(timezone.utc), session_id, url)
    )
    conn.commit()
    cursor.close()
    conn.close()

