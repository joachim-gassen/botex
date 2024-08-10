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
        botex_db, session_id, url, full_conv_history = False,
        model = "gpt-4o", openai_api_key = None,
        local_llm: LocalLLM | None = None, user_prompts: dict | None = None
    ):
    """
    Run a bot on an oTree session. You should not call this function
    directly, but only through the run_single_bot or run_bots_on_session 
    functions.

    Parameters:
    botex_db (str): The name of the SQLite database file to store BotEx data.
    session_id (str): The ID of the oTree session.
    url (str): The participant URL of the bot instance.
    full_conv_history (bool): Whether to keep the full conversation history.
        This will increase token use and only work with very short experiments.
        Default is False.
    model (str): The model to use for the bot. Default is "gpt-4o"
        from OpenAI. You will need an OpenAI key and be prepared to pay to 
        use this model.
    openai_api_key (str): The API key for the OpenAI service.
    local_llm (LocalLLM): A LocalLLM object to use for the bot. If this is not
        None, the bot will use the local model instead of the OpenAI model.
    user_prompts (dict): A dictionary of user prompts to override the default 
        prompts that the bot uses. The keys should be one or more of the 
        following: ['start', 'analyze_first_page_no_q', 'analyze_first_page_q', 
        'analyze_page_no_q', 'analyze_page_q', 'analyze_page_no_q_full_hist', 
        'analyze_page_q_full_hist', 'page_not_changed', 'system', 
        'resp_too_long', 'json_error', 'end'.] If a key is not present in the 
        dictionary, the default prompt will be used. If a key that is not in 
        the default prompts is present in the dictionary, then the bot will 
        exit with a warning and not running to make sure that the user is aware 
        of the issue.

    Returns: None (conversation is stored in the botex database)
    """
    bot_parms = locals()
    bot_parms.pop('local_llm')
    bot_parms['local_llm'] = vars(local_llm) if local_llm else None
    if bot_parms['openai_api_key'] is not None: 
        bot_parms["openai_api_key"] = "******"       
    bot_parms = json.dumps(bot_parms)
    logging.info(f"Running bot with parameters: {bot_parms}")

    def click_on_element(dr, element, timeout = 3600):
        dr.execute_script("arguments[0].scrollIntoView(true)", element)
        element = WebDriverWait(dr, timeout).until(
            EC.element_to_be_clickable(element)
        )
        dr.execute_script("arguments[0].click()", element)

    def set_id_value(dr, id, type, value, timeout = 3600):
        if type != "radio":
            WebDriverWait(dr, timeout).until(
                lambda x: x.find_element(By.ID, id)
            ).send_keys(str(value))
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
        max_attempts = 360
        while attempts < max_attempts:
            try:
                WebDriverWait(dr, timeout).until(
                    lambda x: x.find_element(By.CLASS_NAME, 'otree-form')
                )
                break # Exit the loop if successful
            except TimeoutException:
                attempts += 1
                if attempts % 60 == 0:
                    logging.info(
                        f"Waiting for page to load. Attempt {attempts}/{max_attempts}."
                    )
                continue # Retry if a timeout occurs
        if attempts == max_attempts:
            logging.error(f"Timeout on wait page after {max_attempts} attempts.")
            return 'Timeout on wait page.'

        
    def scan_page(dr):
        dr.get(url)
        text = dr.find_element(By.TAG_NAME, "body").text
        debug_text = dr.find_elements(By.CLASS_NAME, "debug-info")
        if debug_text:
            text = text.replace(debug_text[0].text, "")

        
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
        answer_choices = []
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
                    if type == "radio":
                        # get the answer options
                        options = el[j].find_elements(By.CLASS_NAME, "form-check")
                        answer_choices.append([o.text for o in options])
                    elif el[j].get_attribute("class") == "form-select":
                        # get the answer options
                        options = el[j].find_elements(By.TAG_NAME, "option")
                        answer_choices.append([o.text for o in options[1:]])
                    else:
                        answer_choices.append(None)
                    break
        if question_id != []:
            labels = dr.find_elements(By.CLASS_NAME, "col-form-label")
            question_label = [x.text for x in labels]
            questions = []
            for id, qtype, label, answer_choices in zip(
                question_id, question_type, question_label, answer_choices, strict=True
            ):
                questions.append(
                    {
                        "question_id": id,
                        "question_type": qtype,
                        "question_label": label
                    }
                )
                if answer_choices:
                    questions[-1]["answer_choices"] = answer_choices
        else:
            questions = None
        return (
            text, wait_page, next_button, questions
        )
    
    def llm_send_message(
            message, check_response = None, model = model, questions = None
        ):
        conversation = []
        nonlocal conv_hist_botex_db
        nonlocal conv_hist
        

        def append_message_to_conversation(message):
            nonlocal conversation
            nonlocal conv_hist_botex_db
            conversation.append(message)
            conv_hist_botex_db.append(message)

        if conv_hist: conversation = conv_hist

        resp_dict = None
        error = False
        attempts = 0
        max_attempts = 5
        append_message_to_conversation({"role": "user", "content": message})
        while resp_dict is None:
            if attempts > max_attempts:
                logging.error("The llm did not return a valid response after %s number of attempts." % max_attempts)
                return 'Maximum number of attempts reached.'
            attempts += 1
            if error:
                append_message_to_conversation({"role": "user", "content": message})
                logging.info(
                    f"Sending the following conversation to the llm to fix error: {conversation}"
                )
            if model == "local":
                assert local_llm, "Model is local but local_llm is not set."
                assert conversation, "Conversation is empty."
                resp = local_llm.completion([system_prompt] + conversation)
            else:
                resp =  completion(
                    messages=[system_prompt] + conversation, 
                    model=model, api_key=openai_api_key,
                    response_format = {"type": "json_object"}
                )

            resp_str = resp.choices[0].message.content

            try:
                if error:
                    conversation = conversation[:-2]
                    error = False
                append_message_to_conversation({"role": "assistant", "content": resp_str})
                assert resp_str, "Bot's response is empty."
                start = resp_str.find('{', 0)
                end = resp_str.rfind('}', start)
                resp_str = resp_str[start:end+1]
                resp_dict = json.loads(resp_str, strict = False)
            except (AssertionError, json.JSONDecodeError):
                logging.warning(f"Bot's response is not a valid JSON\n{resp_str}\n. Trying again.")
                resp_dict = None
                error = True
                message = prompts['json_error']
                continue

            if resp.choices[0].finish_reason == "length":
                logging.warning("Bot's response is too long. Trying again.")
                error = True
                message = prompts['resp_too_long']
                continue

            if check_response:
                if questions:
                    success, error_msgs, error_logs = check_response(resp_dict, questions)
                else:
                    success, error_msgs, error_logs = check_response(resp_dict)
                if not success:
                    error = True
                    logging.warning(f"Detected an issue: {' '.join(error_logs)}.\n{resp_dict}.\nAdjusting response.")
                    message = ''
                    for i, error_msg in enumerate(error_msgs):
                        if ':' in error_msg:
                            err, ids = error_msg.split(": ", 1)
                            f_dict = {err: ids}
                            if i == 0:
                                message += prompts[err].format(**f_dict) + ' '
                            else:
                                message += 'Additionally, ' + prompts[err].format(**f_dict) + ' '
                        else:
                            message += prompts[error_msg] + ' '
                    resp_dict = None
                    continue

        if full_conv_history: conv_hist.append(conversation)
        return resp_dict

    def check_response_start(resp):
        check_result = {"error": [], "error_log": []}
        if "error" in resp and resp["error"] != "" and resp["error"] != "None":
            error_log = f"Bot's response indicates error: '{resp['error']}'."
            check_result["error_log"].append(error_log)
            check_result["error"].append("confused")
        if 'understood' not in set(resp):
            error_log = "Bot's response does not have the required understood key."
            check_result["error_log"].append(error_log)
            check_result["error"].append("no_understood_key")
        if str(resp.get('understood')).lower() != "yes":
            error_log = "Bot did not understand the message."
            check_result["error_log"].append(error_log)
            check_result["error"].append("not_understood")
        if check_result.get("error"):
            return False, check_result["error"], check_result["error_log"]
        return True, None, None
        

    def check_response_summary(resp):
        check_result = {"error": [], "error_log": []}
        if "error" in resp and resp["error"] != "" and resp["error"] != "None":
            error_log = f"Bot's response indicates error: '{resp['error']}'."
            check_result["error_log"].append(error_log)
            check_result["error"].append("confused")
        if set(resp) != set(["summary"]):
            error_log = "Bot's response does not have the required set of keys."
            check_result["error_log"].append(error_log)
            check_result["error"].append("no_summary_key")
        
        if check_result.get("error"):
            return False, check_result["error"], check_result["error_log"]
        return True, None, None

    def check_response_question(resp, questions):
        check_result = {"error": [], "error_log": []}
        if "error" in resp and resp["error"] != "" and resp["error"] != "None":
            error_log = f"Bot's response indicates error: '{resp['error']}'."
            check_result["error_log"].append(error_log)
            check_result["error"].append("confused")
        if "summary" not in resp:
            error_log = "Bot's response does not have a summary key"
            check_result["error_log"].append(error_log)
            check_result["error"].append("no_summary_key")
        if "questions" not in resp:
            error_log = "Bot's response does not have a questions key"
            check_result["error_log"].append(error_log)
            check_result["error"].append("no_questions_key")
            return False, check_result["error"], check_result["error_log"]

        if not isinstance(resp['questions'], list):
            if isinstance(resp['questions'], dict):
                resp['questions'] = [resp['questions']]
            else:
                error_log = "Questions is not a list."
                check_result["error_log"].append(error_log)
                check_result["error"].append("questions_not_list")


        q_ids = [q['question_id'] for q in questions]
        answer_ids = [q['id'] for q in resp['questions'] if q.get('id')]
        unanswered_q_ids = set(q_ids) - set(answer_ids)
        if unanswered_q_ids:
            check_result["error_log"].append(f"unanswered_questions: {' '.join(unanswered_q_ids)}")
            check_result["error"].append(f"unanswered_questions: {' '.join(unanswered_q_ids)}")

        errors = {
            "missing_answer": [],
            "missing_reason": [],
            "answer_not_number": [],
            "answer_not_float": [],
            "select_answer_number": [],
            "select_answer_unknown": [],
            "answer_id_not_found_in_q_id_list": []
        }
        for answer in resp['questions']:
            if "id" not in answer:
                continue
            
            if "answer" not in answer:
                errors['missing_answer'].append(answer['id'])
            if "reason" not in answer:
                errors['missing_reason'].append(answer['id'])
            else: 
                if answer['reason'] is None or answer['reason'] == "":
                    errors['missing_reason'].append(answer['id'])
            
            if answer['id'] in q_ids:
                qtype = questions[q_ids.index(answer['id'])]['question_type']
            else:
                errors['answer_id_not_found_in_q_id_list'].append(answer['id'])
                continue
            # 'answer' in answer - because I got answer = {'id': 'id_integer_field', '':''} in the response
            if qtype == 'number' and 'answer' in answer and isinstance(answer['answer'], str):
                try:
                    int_const_pattern = r'[-+]?[0-9]+'
                    rx = re.compile(int_const_pattern, re.VERBOSE)
                    ints = rx.findall(answer['answer'])
                    answer = ints[0]
                except:
                    errors['answer_not_number'].append(answer['id'])
            if qtype == 'float' and 'answer' in answer and isinstance(answer['answer'], str):
                try:
                    numeric_const_pattern = r'[-+]? (?: (?: \d* \. \d+ ) | (?: \d+ \.? ) )(?: [Ee] [+-]? \d+ ) ?'
                    rx = re.compile(numeric_const_pattern, re.VERBOSE)
                    floats = rx.findall(answer['answer'])
                    answer = floats[0]
                except:
                    errors['answer_not_float'].append(answer['id'])
            
            if qtype == 'select-one':
                if not answer['answer'] in questions[q_ids.index(answer['id'])]['answer_choices']:
                    try:
                        int(answer['answer'])
                        errors['select_answer_number'].append(answer['id'])
                    except:
                        errors['select_answer_unknown'].append(answer['id'])
        
        for error in errors:
            if errors[error]:
                check_result["error_log"].append(f"{error}: {errors[error]}")
                check_result["error"].append(f"{error}: {errors[error]}")
        
        if check_result.get("error"):
            return False, check_result["error"], check_result["error_log"]
        return True, None, None
            
    def check_response_end(resp):
        check_result = {"error": [], "error_log": []}
        if "error" in resp and resp["error"] != "" and resp["error"] != "None":
            error_log = f"Bot's response indicates error: '{resp['error']}'."
            check_result["error_log"].append(error_log)
            check_result["error"].append("confused")
        if "remarks" not in resp:
            error_log = "Bot's response does not have the required remarks key."
            check_result["error_log"].append(error_log)
            check_result["error"].append("no_remarks_key")
        if check_result.get("error"):
            return False, check_result["error"], check_result["error_log"]
        return True, None, None
    
    def gracefully_exit_failed_bot(failure_place):
        if failure_place == "start":
            result = "Bot could not even start. Stopping."
        elif failure_place == "abandoned":
            result = "Bot was likely abandoned by its matched participant. Exiting."
        else:
            result = "Bot could not provide a valid response after 5 attempts. Exiting."        
        conv_hist_botex_db.append({"role": "system", "content": result})
        store_data(botex_db, session_id, url, conv_hist_botex_db, bot_parms)
        logging.info("Gracefully exiting failed bot.")
        if failure_place != "start" and failure_place != "end":
            dr.close()
            dr.quit()
    
    def store_data(botex_db, session_id, url, conv, bot_parms):
        """
        Store the conversation data in the BotEx database.

        Parameters:
        botex_db (str): The name of the SQLite database file to store BotEx data.
        session_id (str): The ID of the oTree session.
        url (str): The participant URL of the bot instance.
        conv (list): The conversation data.
        bot_parms (str): The parameters of the bot.

        Returns: None
        """
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
        logging.info("Data stored in botex database.")

    
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
    

    if user_prompts:
        for key in user_prompts:
            if key not in prompts.keys():
                logging.error(f"The bot is exiting because the user prompt that you provided has a key: '{key}' that is not expected by the bot. Please make sure that any default prompts that you want to override are given with the exact same key as the default prompt.")
                return
            else:
                prompts[key] = user_prompts[key]
    
    system_prompt = {
        "role": "system",
        "content": prompts['system']
    }
    message = prompts['start']
    conv_hist_botex_db = [system_prompt]
    conv_hist = []

    resp = llm_send_message(message, check_response_start)
    if resp == 'Maximum number of attempts reached.':
        gracefully_exit_failed_bot("start")
        return
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
            if attempts == 5:
                logging.error("Could not start Chrome after 5 attempts. Stopping.")
                raise   
            time.sleep(1)
        
    first_page = True
    summary = None
    text = ""
    while True:
        old_text = text
        attempts = 0
        while attempts < 5:
            try:
                text, wait_page, next_button, questions = scan_page(dr)
                break
            except:
                attempts += 1
                logging.warning("Failed to scrape my oTree URL. Trying again.")
                if attempts == 5:
                    logging.error("Could not scrape my oTree URL after 5 attempts. Stopping.")
                    gracefully_exit_failed_bot("middle")
                    return
                time.sleep(1)
        
        if wait_page:
            wait_result = wait_next_page(dr)
            if wait_result == 'Timeout on wait page.':
                gracefully_exit_failed_bot("abandoned")
                return
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
            body = text.strip(), summary = summary, nr_q = nr_q,
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
            
        resp = llm_send_message(message, check_response, questions=questions)
        if resp == 'Maximum number of attempts reached.':
            gracefully_exit_failed_bot("middle")
            return

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
    resp = llm_send_message(message, check_response_end)
    if resp == 'Maximum number of attempts reached.':
        gracefully_exit_failed_bot("end")
        return
    logging.info(f"Bot's final remarks about experiment: '{resp}'")
    logging.info("Bot finished.")
    store_data(botex_db, session_id, url, conv_hist_botex_db, bot_parms)






