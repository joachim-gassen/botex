import json
import time
from datetime import datetime, timezone
import sqlite3
import csv
from importlib.resources import files
import re
import logging
logger = logging.getLogger("botex")

import warnings
from importlib.metadata import version, PackageNotFoundError

# Starting with v1.56.2, LiteLLM triggers a user Pydantic user warning
# we will filter this out until the issue is resolved  
try:
    litellm_version = version("litellm")
    logger.info(f"LiteLLM version: {litellm_version}")
except PackageNotFoundError:
    logger.error(f"LiteLLM not installed")

if litellm_version >= "1.56.2":
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        import litellm
else:
    import litellm

litellm.suppress_debug_info = True
litellm.set_verbose = False
logging.getLogger("LiteLLM").setLevel(logging.ERROR)


from pydantic import ValidationError
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .llamacpp import LlamaCpp
from .schemas import create_answers_response_model, EndSchema, Phase, StartSchema, SummarySchema
from .completion import model_supports_response_schema, completion


MAX_NUM_OF_ANSWER_ATTEMPTS = 3
MAX_NUM_OF_SCRAPE_ATTEMPTS = 5
MAX_NUM_OF_ATTEMPTS_TO_START_CHROME = 5

TEST_FORM_VALIDATION_ERRORS = False

def create_prompts(user_prompts):
    with open(
        files('botex').joinpath('bot_prompts.csv'), 
        'r', newline='', encoding='utf-8'
    ) as f:
        rv = csv.reader(f)
        next(rv)
        prompts = {row[0]:row[1].replace(r'\n', '\n') for row in rv}
    
    if user_prompts:
        for key in user_prompts:
            if key not in prompts.keys():
                logger.error(f"The bot is exiting because the user prompt that you provided has a key: '{key}' that is not expected by the bot. Please make sure that any default prompts that you want to override are given with the exact same key as the default prompt.")
                return
            else:
                prompts[key] = user_prompts[key]
    return prompts

def run_bot(**kwargs):
    """
    Run a bot on an oTree session. You should not call this function
    directly, but only through the `run_single_bot()` or 
    `run_bots_on_session()` functions.

    Parameters:
    kwargs (dict): Additional keyword arguments as provided by 
    `run_single_bot()` or `run_bots_on_session()`.

    Returns: None (conversation is stored in the botex database)
    """
    bot_parms = dict(locals(), **kwargs)
    bot_parms.pop('kwargs')

    # The upstream functions will ensure that the following required parameters 
    # are always present in kwargs.
    botex_db = kwargs.pop('botex_db')
    session_id = kwargs.pop('session_id')
    url = kwargs.pop('url')
    model = kwargs.pop('model')
    full_conv_history = kwargs.pop('full_conv_history')
    user_prompts = kwargs.pop('user_prompts')
    prompts = create_prompts(user_prompts)

    if model == "llamacpp":
        llamacpp = LlamaCpp(kwargs.get("api_base"))
        bot_parms['model'] = llamacpp.json_dump_model_cfg()
    else:
        llamacpp = None

    if bot_parms['api_key'] is not None: 
        bot_parms['api_key'] = "******"       
    bot_parms = json.dumps(bot_parms)
    logger.info(f"Running bot with parameters: {bot_parms}")
    if not model_supports_response_schema(model):
        logger.warning(
            f"LiteLLM reports that model '{model}' does not support " +
            "response schema. Will try to use the 'instructor' package " +
            "for response validation. This is alpha and likely to fail."
        )

    def click_on_element(dr, element, timeout = 3600, check_errors = False):
        old_page_source = dr.page_source
        dr.execute_script("arguments[0].scrollIntoView(true)", element)
        element = WebDriverWait(dr, timeout).until(
            EC.element_to_be_clickable(element)
        )
        dr.execute_script("arguments[0].click()", element)
        if not check_errors: return 
        # Find all field validation errors 
        validation_errors = {}
        errors = dr.find_elements(By.CSS_SELECTOR, "input:invalid")
        if len(errors) == 0: return validation_errors
        for e in errors:
            if e.get_attribute("validationMessage"): 
                validation_errors[e.get_attribute("id")] = {
                    "label": e.accessible_name,
                    "validation_message": e.get_attribute("validationMessage")
                }
        if len(validation_errors) == 0: return validation_errors
        url = dr.current_url
        dr.get(url)
        if not (dr.page_source == old_page_source):
            # We are on the next page - no validation errors
            return {}
        return validation_errors

    def set_id_value(dr, id, type, value, timeout = 3600):
        if type == "button-radio":
            resp = dr.find_elements(By.CLASS_NAME, "btn")
            for r in resp:
                if r.text == value:
                    click_on_element(dr, r)
                    break
        elif type != "radio":
            WebDriverWait(dr, timeout).until(
                lambda x: x.find_element(By.ID, id)
            ).send_keys(str(value))
        else :
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
                    logger.info(
                        f"Waiting for page to load. Attempt {attempts}/{max_attempts}."
                    )
                continue # Retry if a timeout occurs
        if attempts == max_attempts:
            logger.error(f"Timeout on wait page after {max_attempts} attempts.")
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
        question_label = []
        btns = dr.find_elements(By.CLASS_NAME, 'btn')
        for b in btns:
            id = b.get_attribute('name')
            if id is None or id == '': continue
            else: id = "id_" + id
            if id not in question_id:
                question_id.append(id)
                question_type.append("button-radio")
                question_label.append('Select a button')
                answer_choices.append([b.text])
            else:
                answer_choices[question_id.index(id)].append(b.text) 
        fe = dr.find_elements(By.CLASS_NAME, 'controls')
        # We use a different element attribute now (see below)
        # But I leave the old code in case that the new approach
        # is not robust. 
        # labels = dr.find_elements(By.CLASS_NAME, "col-form-label")
        lc = 0
        for i in range(len(fe)): 
            el = fe[i].find_elements(By.XPATH, ".//*")
            for j in range(len(el)):
                id = el[j].get_attribute("id")
                if id != '': 
                    question_id.append(id)
                    # question_label.append(labels[lc].text)
                    # lc += 1
                    question_label.append(el[j].accessible_name)
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
            questions = {}
            for id, qtype, label, answer_choices in zip(
                question_id, question_type, question_label, answer_choices, 
                strict=True
            ):
                questions[id] = {
                    "question_type": qtype, "question_label": label
                }
                if answer_choices:
                    questions[id]["answer_choices"] = answer_choices
        else:
            questions = None
        return (
            text, wait_page, next_button, questions
        )
    
    def llm_send_message(
            message, phase: Phase, check_response = None, model = model, 
            questions = None
        ):
        conversation = []
        nonlocal conv_hist_botex_db
        nonlocal conv_hist

        # set schemas
        if phase == Phase.start:
            response_format = StartSchema
        elif phase == Phase.middle:
            if questions:
                response_format = create_answers_response_model(questions)
            else:
                response_format = SummarySchema
        elif phase == Phase.end:
            response_format = EndSchema
        else:
            raise ValueError("Invalid phase.")

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
                logger.error("The llm did not return a valid response after %s attempts." % max_attempts)
                return 'Maximum number of attempts reached.'
            attempts += 1
            if error:
                append_message_to_conversation({"role": "user", "content": message})
                logger.info(
                    f"Sending the following conversation to the llm to fix error:\n{json.dumps(conversation, indent=4)}"
                )
            
            resp = completion(
                llamacpp=llamacpp, model=model,
                messages=[system_prompt] + conversation, 
                response_format=response_format,
                **kwargs
            )
            resp_str = resp['resp_str']

            if error:
                conversation = conversation[:-2]

            append_message_to_conversation({"role": "assistant", "content": resp_str})
            
            if resp['finish_reason'] == "length":
                logger.warning("Bot's response is too long. Trying again.")
                error = True
                message = prompts['resp_too_long']
                continue

            try:
                assert resp_str, "Bot's response is empty."
                start = resp_str.find('{', 0)
                end = resp_str.rfind('}', start)
                resp_str = resp_str[start:end+1]
                resp_dict = json.loads(resp_str, strict = False)
                error = False
            except (AssertionError, json.JSONDecodeError):
                logger.warning("Bot's response is not a valid JSON.")
                resp_dict = None
                error = True
                message = prompts['json_error']
                continue


            if check_response:
                success, error_msgs, error_logs = check_response(resp_dict, response_format)
                if not success:
                    error = True
                    logger.warning(f"Detected an issue: {' '.join(error_logs)}.")
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

        if full_conv_history: conv_hist = conversation.copy()
        return resp_dict
    
    def validate_response(resp, schema, check_result):
        try:
            schema.model_validate_json(json.dumps(resp))
        except ValidationError as e:
            e = json.loads(e.json())[0]['msg']
            e_log = f"Bot's response does not respect the schema: {e}."
            check_result['error_log'].append(e_log)
            check_result['error'].append(f"schema_error: {e}")
            return check_result
        return check_result

    def check_response_start(resp, response_format):
        check_result = {"error": [], "error_log": []}
        check_result = validate_response(resp, response_format, check_result)
        
        if not resp['understood']:
            error_log = "Bot did not understand the message."
            check_result["error_log"].append(error_log)
            check_result["error"].append("not_understood")

        if check_result.get("error"):
            return False, check_result["error"], check_result["error_log"]
        return True, None, None
        

    def check_response_middle(resp, response_format):
        check_result = {"error": [], "error_log": []}
        check_result = validate_response(resp, response_format, check_result)
        
        if resp["confused"]:
            check_result["error_log"].append("Bot is confused.")
            check_result["error"].append("confused")


        if check_result.get("error"):
            return False, check_result["error"], check_result["error_log"]
        return True, None, None

            
    def check_response_end(resp, response_format):
        check_result = {"error": [], "error_log": []}
        check_result = validate_response(resp, response_format, check_result)

        if resp["confused"]:
            check_result["error_log"].append("Bot is confused.")
            check_result["error"].append("confused")
        if check_result.get("error"):
            return False, check_result["error"], check_result["error_log"]
        return True, None, None
    
    def gracefully_exit_failed_bot(failure_place):
        if failure_place == "start":
            result = "Bot could not even start. Stopping."
        elif failure_place == "abandoned":
            result = "Bot was likely abandoned by its matched participant. Exiting."
        else:
            result = "Bot could not provide a valid response. Exiting."        
        conv_hist_botex_db.append({"role": "system", "content": result})
        store_data(botex_db, session_id, url, conv_hist_botex_db, bot_parms)
        logger.info("Gracefully exiting failed bot.")
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
        logger.info("Data stored in botex database.")

    
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

    if full_conv_history:
        system_prompt = {
            "role": "system",
            "content": prompts['system_full_hist']
        }    
    else:
        system_prompt = {
            "role": "system",
            "content": prompts['system']
        }
        
    message = prompts['start']
    conv_hist_botex_db = [system_prompt]
    conv_hist = []

    resp = llm_send_message(message, Phase.start, check_response_start)
    if resp == 'Maximum number of attempts reached.':
        gracefully_exit_failed_bot("start")
        return
    logger.info(f"Bot's response to start message:\n{json.dumps(resp, indent=4)}")
    
    options = Options()
    options.add_argument("--headless=new")
    # Needed to work on codespaces but might be a security risk on
    # untrusted web pages
    options.add_argument("--no-sandbox")
    # Should result in only fatal errors being logged
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    attempts = 0
    while attempts < MAX_NUM_OF_ATTEMPTS_TO_START_CHROME:
        try:
            dr = webdriver.Chrome(options = options)
            dr.set_window_size(1920, 1400)
            break
        except:
            attempts += 1
            logger.warning("Could not start Chrome. Trying again.")
            if attempts == 5:
                logger.error(f"Could not start Chrome after {MAX_NUM_OF_ATTEMPTS_TO_START_CHROME} attempts. Stopping.")
                raise   
            time.sleep(1)
        
    first_page = True
    summary = None
    text = ""
    answer_attempts = 0
    validation_errors = {}
    if TEST_FORM_VALIDATION_ERRORS: first_try = True
    while True:
        old_text = text
        attempts = 0
        while attempts < MAX_NUM_OF_SCRAPE_ATTEMPTS:
            try:
                text, wait_page, next_button, questions = scan_page(dr)
                break
            except:
                attempts += 1
                logger.warning("Failed to scrape my oTree URL. Trying again.")
                if attempts == 5:
                    logger.error(f"Could not scrape my oTree URL after {MAX_NUM_OF_SCRAPE_ATTEMPTS} attempts. Stopping.")
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
        else:
            nr_q = len(questions)
            questions_json = json.dumps(questions)
        check_response = check_response_middle

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
            if answer_attempts > MAX_NUM_OF_ANSWER_ATTEMPTS:
                logger.error(
                    f"Bot could not provide valid answers after {MAX_NUM_OF_ANSWER_ATTEMPTS} attempts. Stopping."
                )
                gracefully_exit_failed_bot("middle")
                return
            answer_attempts += 1
            if questions == None:
                logger.warning(
                    "Same page encountered twice. "
                    "This should only happen with pages containing questions. "
                    "Most likely something is seriously wrong here."
                )
                message = prompts['page_not_changed_no_vm'] + message
            else:
                if validation_errors:
                    logger.info("Informing bot about validation errors.")
                    message = prompts['page_not_changed_vm'].format(
                        validation_errors_json = json.dumps(validation_errors)
                    ) + message
                    validation_errors = {}
                else: 
                    logger.warning(
                        "Bot's answers were likely erroneous, but no validation "
                        "errors were found. This should not happen."
                        "Most likely something is seriously wrong here."
                    )
                    message = prompts['page_not_changed_no_vm'] + message

        resp = llm_send_message(
            message, Phase.middle, check_response, questions=questions
        )
        if resp == 'Maximum number of attempts reached.':
            gracefully_exit_failed_bot("middle")
            return

        logger.info(f"Bot's analysis of page:\n{json.dumps(resp, indent=4)}")
        if not full_conv_history: summary = resp['summary']
        if questions is None and next_button is not None:
            logger.info("Page has no question but next button. Clicking")
            click_on_element(dr, next_button)
            continue
        
        if questions is None and next_button is None:
            logger.info("Page has no question and no next button. Stopping.")
            break

        logger.info(f"Page has {len(questions)} question(s).")

        for id_, a in resp['answers'].items(): 
            logger.info(
                "Bot has answered question " + 
                f"'{id_}' with '{a['answer']}'."
            )
            answer = a['answer']
            try:
                qtype = questions[id_]['question_type']
            except:
                logger.warning(f"Question '{id_}' not found in questions.")
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
            
            if TEST_FORM_VALIDATION_ERRORS and id_ == 'id_integer_field': 
                if first_try:
                    logger.info(
                        f"Answering question {id_} with 'blue' instead of {answer} "
                        "to test form validation errors."
                    )
                    answer = "blue"
                    resp['answers'][id_]['answer'] = answer
                    first_try = False
            set_id_value(dr, id_, qtype, answer)

        if qtype is not None and next_button: 
            validation_errors = click_on_element(
                dr, next_button, check_errors=True
            )
            if validation_errors:
                if not set(validation_errors.keys()).issubset(resp['answers'].keys()):
                    logger.warn(
                        "The validation errors returned by oTree do not match the questions. "
                        "This should not happen. "
                        "Most likely something is seriously wrong here."
                    )
                    validation_errors = {}
                else:
                    for id_, v in validation_errors.items():
                        validation_errors[id_]["invalid_answer"] = resp['answers'][id_]['answer']
                    logger.warning(
                        f"oTree returned validation errors: {validation_errors}"
                    )
         
    
    dr.close()
    dr.quit()
    message = prompts['end_full_hist'] if full_conv_history else prompts['end'].format(summary = summary)
    resp = llm_send_message(message, Phase.end, check_response_end)
    if resp == 'Maximum number of attempts reached.':
        gracefully_exit_failed_bot("end")
        return
    logger.info(f"Bot's final remarks about experiment:\n{json.dumps(resp, indent=4)}")
    logger.info("Bot finished.")
    store_data(botex_db, session_id, url, conv_hist_botex_db, bot_parms)
