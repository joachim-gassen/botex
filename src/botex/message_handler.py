import logging
import json
from typing import Callable, Optional, Dict, Tuple
from threading import Lock
from .local_llm import LocalLLM, HumanMessage, AIMessage, ChatHistory
from .config import PromptsConfig, LLMConfig


class MessageHandler:
    """
    Handles messaging with a language model, managing both local and potentially remote model communications.

    :param llm_cfg: Configuration for the local or remote language model.
    :param prompts: Configuration containing various prompts for interaction stages.
    :param full_conv_history: Flag to maintain full conversation history. Defaults to False.
    """

    def __init__(
        self,
        llm_cfg: LLMConfig,
        prompts: PromptsConfig,
        full_conv_history: bool = False,
    ) -> None:
        if llm_cfg["model"] == "local":
            self.llm = LocalLLM(
                system_prompt=llm_cfg["system_prompt"],
                path_to_compiled_llama_cpp_main_file=llm_cfg[
                    "path_to_compiled_llama_cpp_main_file"
                ],
                local_model_cfg=llm_cfg["local_model_cfg"],
                system_prompt_few_shot_examples=llm_cfg[
                    "system_prompt_few_shot_examples"
                ],
            )
        self.full_conv_history = full_conv_history
        self.prompts = prompts
        self.model = llm_cfg["model"]

    def llm_send_message(self, message, conv_hist, check_response=None, **kwargs):
        """
        Dispatches a message to the language model and processes the response, handling retries and validations.

        :param message: The message string to send to the language model.
        :param conv_hist: The current chat history to include in the prompt.
        :param check_response: An optional callable for additional validation of the model's response.
        :param kwargs: Additional keyword arguments, specifically expects 'lock' when calling local model.
        :return: A tuple containing the model's response as a dictionary and the updated conversation history.
        """
        if self.model == "local":
            return self.llm_send_message_local(
                message, conv_hist, kwargs["lock"], check_response
            )
        else:
            return self.llm_send_message_remote(message, conv_hist, check_response)

    def llm_send_message_local(
        self,
        message: str,
        conv_hist: ChatHistory,
        lock: Lock,
        check_response: Optional[Callable[[Dict], Dict]] = None,
    ) -> Tuple[dict, ChatHistory]:
        """
        Handles message dispatch to a local language model with retries and response validation.

        :param message: The message string to send.
        :param conv_hist: The conversation history to include.
        :param lock: A threading lock to ensure thread-safe operations.
        :param check_response: An optional callable for validating the response.
        :return: A tuple of the response dictionary and the updated conversation history.
        :raises ValueError: If a satisfactory response is not received after a set number of retries.
        """
        assert self.llm is not None, "Local model requires an instance of LocalLLM."
        max_retries = 5

        with lock:
            hist = conv_hist if self.full_conv_history else ChatHistory([])
            for _ in range(max_retries):
                resp, finish = self.llm.generate(HumanMessage(message), hist)
                hist.extend([HumanMessage(message), AIMessage(resp)])
                if finish == "length":
                    logging.warning("Bot's response is too long. Trying again")
                    message = self.prompts["resp_too_long"]
                    continue

                if self.is_response_valid(resp):
                    resp = json.loads(resp)
                    if check_response:
                        success, error_msg = check_response(resp)
                        if not success:
                            logging.warning(
                                f"Issue detected: {error_msg}. Adjusting response."
                            )
                            if error_msg.startswith("question_id"):
                                message = self.prompts[
                                    "missing_keys_in_question"
                                ].format(missing_question_keys=error_msg)
                            else:
                                message = self.prompts[error_msg]
                            continue
                    conv_hist.extend(hist)
                    return resp, conv_hist
                else:
                    logging.warning("Bot's response is not a valid JSON. Trying again")
                    message = self.prompts["json_error"]
                    continue
            logging.error(
                "Failed to receive a satisfactory response after %s retries."
                % max_retries
            )
            raise ValueError("Unsatisfactory response from LLM. Exiting...")

    def is_response_valid(self, response: str) -> bool:
        """
        Validates if the response from the language model is a valid JSON string.

        :param response: The response string from the language model.
        :return: True if the response is a valid JSON string, False otherwise.
        """
        try:
            json.loads(response)
            return True
        except json.JSONDecodeError:
            logging.error("Failed to decode JSON response.")
            return False

    def check_response_start(self, resp: Dict) -> Tuple[bool, str]:
        """
        Checks the initial response from the language model to determine if the conversation can proceed.

        :param resp: The dictionary response from the language model.
        :return: A tuple containing a boolean indicating success or failure, and a string indicating the specific status.
        """
        if "error" in resp:
            return False, "confused"
        if not "understood" in resp or str(resp["understood"]).lower() != "yes":
            return False, "not_understood"
        return True, "success"

    def check_response_summary(self, resp: Dict) -> Tuple[bool, str]:
        """
        Verifies if the response from the language model includes a summary as expected.

        :param resp: The dictionary response from the language model.
        :return: A tuple indicating success or failure, and a string describing the specific issue if failed.
        """
        if "error" in resp:
            return False, "confused"
        if not "summary" in resp:
            return False, "no_summary"
        return True, "success"

    def check_response_question(self, resp: Dict) -> Tuple[bool, str]:
        """
        Validates the questions section in the model's response, checking for completeness and format.

        :param resp: The dictionary response from the language model.
        :return: A tuple indicating success or failure, and a string describing the specific errors if failed.
        """
        if "error" in resp:
            return False, "confused"
        if "questions" not in resp:
            return False, "no_questions"
        if not isinstance(resp["questions"], list):
            return False, "questions_not_list"

        detailed_errors = []
        for index, question in enumerate(resp["questions"]):
            missing_keys = [
                key for key in ["id", "answer", "reason"] if key not in question
            ]
            if missing_keys:
                question_id = question.get("id", f"unknown_id_{index}")
                detailed_errors.append(
                    f"question_id '{question_id}' missing keys: {', '.join(missing_keys)}"
                )

        if detailed_errors:
            error_message = "; ".join(detailed_errors)
            return False, error_message
        return True, "success"

    def check_response_end(self, resp: Dict) -> Tuple[bool, str]:
        """
        Examines the final response from the language model to determine if the interaction concluded appropriately.

        :param resp: The dictionary response from the language model.
        :return: A tuple indicating success or failure, and a string describing the issue if the interaction did not conclude properly.
        """
        if "error" in resp:
            return False, "error"
        if not "remarks" in resp:
            return False, "no_remarks"
        return True, "success"

    def llm_send_message_remote(self, message, conv_hist, check_response=None):
        """
        Handles message dispatch to a remote language model. Not implemented yet.

        :param message: The message string to send.
        :param conv_hist: The conversation history to include in the prompt.
        :param check_response: An optional callable for additional response validation.
        :raises NotImplementedError: If the method is called, since remote functionality is not yet implemented.
        """
        raise NotImplementedError("Remote LLM not implemented yet.")
