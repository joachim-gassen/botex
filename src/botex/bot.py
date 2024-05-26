import logging
import json
import re
from datetime import datetime, timezone
from threading import Lock


from .db_manager import DatabaseManager
from .local_llm import ChatHistory
from .message_handler import MessageHandler
from .web_interaction_handler import WebInteractionHandler


class Bot:
    """
    Manages a single bot operation within an oTree session.
    """

    def __init__(
        self,
        session_id: str,
        # lock: Lock,
        otree_server_url: str,
        otree_rest_key: str,
        db_manager: DatabaseManager,
        web_interaction_handler: WebInteractionHandler,
        message_handler: MessageHandler,
    ):
        self.db_manager = db_manager
        self.session_id = session_id
        self.otree_server_url = otree_server_url
        self.otree_rest_key = otree_rest_key
        # self.lock = lock
        self.wh = web_interaction_handler
        self.mh = message_handler
        self.prompts = self.mh.prompts
        self.full_conv_history = self.mh.full_conv_history
        self.bot_parms = {
            "llm_parms": vars(self.mh.llm),
            "botex_parms": {
                "botex_db": self.db_manager.db_path,
                "session_id": self.session_id,
                "otree_server_url": self.otree_server_url,
                "full_conv_history": self.full_conv_history,
                "otree_rest_key": self.otree_rest_key,
                "bot_prompts": self.prompts,
            },
        }

    def run_bot(self, url: str, lock: Lock):
        """
        Operates a single bot on a given URL using a web driver controlled by the WebInteractionHandler.

        :param url: The URL for the bot to operate on.
        :param lock: A threading lock to ensure thread-safe operations during web interactions.
        """
        driver = self.wh.create_driver()
        self.db_manager.update_participant(
            self.session_id, url[-8:], datetime.now(timezone.utc).isoformat()
        )

        message = self.prompts["start"]
        conv = ChatHistory([])
        resp, conv = self.mh.llm_send_message(
            message, conv, self.mh.check_response_start, lock=lock
        )
        logging.info(f"Bot's response to start message: '{resp}'")

        first_page = True
        summary = None
        text = ""
        while True:
            old_text = text
            text, wait_page, next_button, questions = self.wh.scan_page(
                driver, url
            ).values()
            if wait_page:
                self.wh.wait_next_page(driver)
                continue

            if self.full_conv_history:
                if questions:
                    analyze_prompt = "analyze_page_q_full_hist"
                else:
                    analyze_prompt = "analyze_page_no_q_full_hist"
            else:
                if first_page:
                    if questions:
                        analyze_prompt = "analyze_first_page_q"
                    else:
                        analyze_prompt = "analyze_first_page_no_q"
                else:
                    if questions:
                        analyze_prompt = "analyze_page_q"
                    else:
                        analyze_prompt = "analyze_page_no_q"
            if questions == None:
                nr_q = 0
                questions_json = ""
                check_response = self.mh.check_response_summary
            else:
                nr_q = len(questions)
                questions_json = json.dumps(questions)
                check_response = self.mh.check_response_question

            message = self.prompts[analyze_prompt].format(
                body=text.strip(),
                summary=summary,
                nr_q=nr_q,
                questions_json=questions_json.strip(),
            )

            if first_page:
                first_page = False
                if self.full_conv_history:
                    message = re.sub(
                        "You have now proceeded to the next page\\.",
                        "You are now on the starting page of the survey/experiment\\.",
                        message,
                    )

            if old_text == text:
                logging.warning("Bot's answers were likely erroneous. Trying again.")
                if questions == None:
                    logging.warning(
                        """
                        This should only happen with pages containing questions.
                        Most likely something is seriously wrong here.
                    """
                    )
                message = self.prompts["page_not_changed"] + message

            resp, conv = self.mh.llm_send_message(
                message, conv, check_response, lock=lock
            )
            logging.info(f"Bot analysis of page: '{resp}'")
            if not self.full_conv_history:
                summary = resp["summary"]
            if questions is None and next_button is not None:
                logging.info("Page has no question but next button. Clicking")
                self.wh.click_on_element(driver, next_button)
                continue

            if questions is None and next_button is None:
                logging.info("Page has no question and no next button. Stopping.")
                break

            logging.info(f"Page has {len(questions)} question(s).")
            for q in resp["questions"]:
                logging.info(
                    "Bot has answered question " + f"'{q['id']}' with '{q['answer']}'."
                )
                answer = q["answer"]
                try:
                    qtype = next(
                        qst["question_type"]
                        for qst in questions
                        if qst["question_id"] == q["id"]
                    )
                except:
                    logging.warning(f"Question '{q['id']}' not found in questions.")
                    qtype = None
                    break

                if qtype == "number" and isinstance(answer, str):
                    int_const_pattern = r"[-+]?[0-9]+"
                    rx = re.compile(int_const_pattern, re.VERBOSE)
                    ints = rx.findall(answer)
                    answer = ints[0]
                if qtype == "float" and isinstance(answer, str):
                    numeric_const_pattern = r"[-+]? (?: (?: \d* \. \d+ ) | (?: \d+ \.? ) )(?: [Ee] [+-]? \d+ ) ?"
                    rx = re.compile(numeric_const_pattern, re.VERBOSE)
                    floats = rx.findall(answer)
                    answer = floats[0]
                if qtype == "radio" and isinstance(answer, bool):
                    answer = "Yes" if answer else "No"
                if qtype == "radio" and isinstance(answer, int):
                    # This is a bit of a hack and last ditch effort to get the answer. Could be problematic depending on the indexing used by the llm. But by providing the answer options in the prompt, the llm should pick the text version of the answer.
                    for question in questions:
                        if question["question_id"] == q["id"]:
                            answer = question["answer_options"][answer]
                if qtype == "select-one" and isinstance(answer, int):
                    # This is a bit of a hack and last ditch effort to get the answer. Could be problematic depending on the indexing used by the llm. But by providing the answer options in the prompt, the llm should pick the text version of the answer.
                    for question in questions:
                        if question["question_id"] == q["id"]:
                            answer = question["answer_options"][answer]
                # I guess select many would also look similar to this.
                self.wh.set_id_value(driver, q["id"], qtype, answer)

            if qtype is not None:
                self.wh.click_on_element(driver, next_button)

        self.wh.close_driver(driver)
        message = self.prompts["end"].format(summary=summary)
        resp, conv = self.mh.llm_send_message(
            message, conv, self.mh.check_response_end, lock=lock
        )
        logging.info(f"Bot's final remarks about experiment: '{resp}'")
        logging.info("Bot finished.")

        self.db_manager.insert_conversation(url[-8:], self.bot_parms, conv)
        self.db_manager.update_participant(
            self.session_id, url[-8:], datetime.now(timezone.utc).isoformat()
        )
