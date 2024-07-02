import logging
from jinja2 import Template
import os
import psutil
import requests
import subprocess
import time
from typing import List, Union, Iterable
from urllib.parse import urlparse

from .gguf_parser import GGUFParser


class Message(dict):
    """
    Represents a generic message within a chat history.

    :param role: The role of the message sender ('user', 'assistant', or 'system').
    :param content: The textual content of the message.
    :raises ValueError: If content is empty or role is not one of the specified values.
    """

    def __init__(self, role: str, content: str) -> None:
        super().__init__({"role": role, "content": content})
        if isinstance(role, str) and role in ["user", "assistant", "system"]:
            self.role = role
        else:
            raise ValueError("Role must be 'user', 'assistant' or 'system'.")

    def to_text(self) -> str:
        return f'{self.role}: {self["content"]}'


class HumanMessage(Message):
    """
    Represents a message sent by a human user.
    """

    def __init__(self, content: str) -> None:
        super().__init__("user", content)


class AIMessage(Message):
    """
    Represents a message sent by an AI system.
    """

    def __init__(self, content: str) -> None:
        super().__init__("assistant", content)


class SystemMessage(Message):
    """
    Represents a message that conveys system-level information for the ai.
    """

    def __init__(self, content: str) -> None:
        super().__init__("system", content)


class ChatHistory(list):
    """
    Manages a history of messages in a conversation, facilitating tracking of dialogue context.

    :param messages: A single message or a list of messages to initialize the history.
    :raises ValueError: If messages are not in an acceptable format.
    """

    def __init__(self, messages: Union[Message, List[Message]]) -> None:
        role_class_map = {
            "user": HumanMessage,
            "assistant": AIMessage,
            "system": SystemMessage,
        }
        if isinstance(messages, Message):
            messages = [messages]
        elif isinstance(messages, list):
            if all(isinstance(message, dict) for message in messages):
                new_messages = []
                for message in messages:
                    if "role" in message and "content" in message:
                        new_messages.append(
                            role_class_map[message["role"]](message["content"])
                        )
                    else:
                        raise ValueError(
                            "All messages must have a 'role' and 'content' key."
                        )
                messages = new_messages
            if not all(isinstance(message, Message) for message in messages):
                raise ValueError(
                    "All messages must be of type Message, either HumanMessage or AIMessage."
                )
        else:
            raise ValueError(
                "Invalid input. Messages must be a Message object or a list of Message objects."
            )
        super().__init__(messages)

    def extend(self, iterable: Iterable) -> None:
        if not all(isinstance(element, dict) for element in iterable):
            raise ValueError(
                "All elements in the iterable must be dictionaries with 'role' and 'content' keys."
            )
        for element in iterable:
            if "role" in element and "content" in element:
                self.append(Message(element["role"], element["content"]))
            else:
                raise ValueError("All messages must have a 'role' and 'content' key.")

    def to_text(self) -> str:
        chat_history = ""
        for message in self:
            chat_history += message.to_text() + "\\\n"
        return chat_history


class MirrorLiteLLMResponse:
    def __init__(self, content, finish_reason):
        self._content = content
        self.finish_reason = finish_reason
        self.choices = [self]

    @property
    def message(self):
        return self

    @property
    def content(self):
        return self._content


class LocalLLM:
    """
    A class to manage local execution of a language model using a compiled main file and configuration.

    :param sys_prompt: The initial system prompt for the language model.
    :param sys_prompt_few_shot_examples: Predefined few-shot examples as a part of the system prompt.
    :param path_to_compiled_llama_cpp_main_file: Path to the compiled main file of the llama_cpp project.
    :param model: A dictionary containing model configurations specific to the local model setup.
    """

    def __init__(
        self,
        path_to_compiled_llama_server_executable: str,
        local_model_path: str,
        api_base_url: str = "http://localhost:8080",
        system_prompt_few_shot_examples: ChatHistory | None = None,
        has_system_role: bool = False,
        ngl: int = 1,
        temp: float = 0.5,
        n: int = 10000,
        top_p: float = 0.9,
        top_k: int = 40,
        num_slots: int = 1,
        **kwargs,
    ):
        self.system_prompt_few_shot_examples = system_prompt_few_shot_examples
        self.server_path = path_to_compiled_llama_server_executable
        self.model_path = local_model_path
        self.api_base_url = api_base_url
        parsed_gguf = GGUFParser(self.model_path)
        self.metadata = parsed_gguf.get_metadata()
        self.has_system_role = (
            has_system_role
            if isinstance(has_system_role, bool)
            else eval(has_system_role)
        )
        self.ngl = ngl
        self.c = self.metadata.get("context_length", 32768)
        self.temp = temp
        self.n = n
        self.top_p = top_p
        self.top_k = top_k
        self.num_slots = num_slots

    def validate_parameters(self):
        if not os.path.exists(self.server_path):
            raise FileNotFoundError(f"Server path not found: {self.server_path}")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model path not found: {self.model_path}")

    def start_server(self):
        """
        Starts the local language model server.
        """
        self.validate_parameters()

        parsed_url = urlparse(self.api_base_url)
        cmd = [
            self.server_path,
            "--host",
            parsed_url.hostname,
            "--port",
            str(parsed_url.port),
            "-ngl",
            str(self.ngl),
            "--reverse_prompt",
            "\n\n\n\n\n\n\n\n\n\n\n\n\n\n",
            "--reverse_prompt",
            "\t\t\t\t\t\t\t\t\t\t\t\t\t\t",
            "--reverse_prompt",
            " \n  \n  \n  \n  \n  \n  \n  \n  ",
            "-m",
            self.model_path,
            "-c",
            str(int(self.num_slots) * (int(self.c) + int(self.n))),
            "-n",
            str(self.n),
            "--parallel",
            str(self.num_slots),
            "-fa",
        ]
        logging.info(f"Starting LLM server ...")
        with open("llama_cpp_server.log", "a") as log_file:
            process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.PIPE)

        if self.wait_for_server(parsed_url.hostname, parsed_url.port):
            logging.info("LLM server started successfully.")
            return process

        _, stderr = process.communicate(timeout=10)
        if process.returncode != 0 and stderr:
            logging.error("Failed to start the LLM server.")
            if "cudaMalloc failed: out of memory" in stderr.decode("utf-8"):
                raise Exception(
                    f"Failed to start the LLM server. Your model {self.model_path} is too large for the available GPU memory. Please try a smaller model or decrease the number of layers, {self.ngl} that are offloaded to the GPU."
                )
            raise Exception(
                f"Failed to start the LLM server. Error: {stderr.decode('utf-8')}"
            )

        if self.wait_for_server(parsed_url.hostname, parsed_url.port):
            logging.info("LLM server started successfully.")
            return process
        else:
            logging.error("Failed to start the LLM server.")
            process.terminate()
            return None

    def wait_for_server(self, host, port, timeout=10):
        """
        Waits for the server to become responsive.
        """
        url = f"http://{host}:{port}/health"
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    return True
            except requests.ConnectionError:
                time.sleep(1)
        return False

    def stop_server(self, process: subprocess.Popen):
        """
        Stops the local language model server.
        """
        if process:
            logging.info("Stopping server...")
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()

            process.wait()
            logging.info("Server stopped.")
        else:
            logging.warning("Server is not running.")

    def prepare_prompt(
        self,
        chat_history: ChatHistory,
        question: Union[HumanMessage, str] | None = None,
    ) -> str:
        """
        Prepares a full prompt from a given question and chat history by applying formatting to fit the model's template.

        :param question: A human message or a string that represents the question to be answered.
        :param chat_history: The chat history instance containing previous conversation context.
        """
        if not isinstance(chat_history, ChatHistory):
            chat_history = ChatHistory(chat_history)
        if question and not isinstance(question, (HumanMessage, str)):
            raise ValueError("question must be of type HumanMessage or str.")
        if isinstance(question, str):
            question = HumanMessage(question)

        full_prompt = [*chat_history, question] if question else chat_history

        if self.system_prompt_few_shot_examples:
            full_prompt = ChatHistory(
                full_prompt[:1] + self.system_prompt_few_shot_examples + full_prompt[1:]
            )
        return self.format_prompt_to_template(full_prompt)  # type: ignore

    def format_prompt_to_template(self, messages: ChatHistory) -> str:
        """
        Formats a chat history into a prompt template suitable for model processing, handling tokenization and templating.

        :param messages: The chat history instance to format.
        :raises FileNotFoundError: If essential tokenizer configuration files are missing.
        """
        # using Mistral 7b v3 instruct template as default
        default_chat_template = """
        {{ bos_token }}{% for message in messages %}{% if (message['role'] == 'user') != (loop.index0 % 2 == 0) %}{{ raise_exception('Conversation roles must alternate user/assistant/user/assistant/...') }}{% endif %}{% if message['role'] == 'user' %}{{ '[INST] ' + message['content'] + ' [/INST]' }}{% elif message['role'] == 'assistant' %}{{ message['content'] + eos_token}}{% else %}{{ raise_exception('Only user and assistant roles are supported!') }}{% endif %}{% endfor %}
        """

        if not self.metadata.get("chat_template"):
            logging.warning(
                "No chat template found in the metadata of the model. Using default template from Mistral 7b v3 instruct. This might severely affect the model's performance. Also keep in mind there is no system role in the default template."
            )
            self.metadata["chat_template"] = default_chat_template
            self.has_system_role = False

        template = Template(self.metadata["chat_template"])  # type: ignore

        if not self.has_system_role:
            messages = self.push_system_message_to_user(messages)

        return template.render(
            messages=messages, add_generation_prompt=True, **self.metadata
        )

    @staticmethod
    def push_system_message_to_user(messages: ChatHistory) -> ChatHistory:
        """
        Adjusts the chat history by merging system messages into subsequent human messages. This is necessary for models that do not support system messages.

        :param messages: The original chat history that may include system messages.
        :return: A modified ChatHistory where system messages are integrated into the next human message.
        """
        for i, message in enumerate(messages):
            if isinstance(message, SystemMessage):
                messages[i + 1] = HumanMessage(
                    message["content"] + "\n" + messages[i + 1]["content"]
                )
                messages.pop(i)
        return messages

    def completion(self, messages) -> MirrorLiteLLMResponse:
        """
        Generates a completion by setting up the prompt, running the local language model, and processing its output.

        :param question: The question to be answered by the model.
        :param chat_history: The current chat history for context.
        :return: A tuple containing the generated completion and the finish reason.
        :raises Exception: If there is an error during the execution of the model command.
        """
        prompt = self.prepare_prompt(messages)

        url = f"{self.api_base_url}/completion"

        payload = {
            "prompt": prompt,
            "temperature": self.temp,
            "cache_prompt": False,
            "max_tokens": self.n,
        }

        attempts = 0
        while True:
            try:
                response = requests.post(url, json=payload, timeout=300)
                break
            except requests.Timeout:
                logging.error("Request timed out. Retrying...")
                attempts += 1
                if attempts == 3:
                    raise Exception("Request timed out after 3 attempts.")
                

        if response.status_code != 200:
            raise Exception(
                f"An error occurred while generating the completion: {response.text}"
            )

        completion = response.json()["content"]
        finish_reason = "length" if response.json()["stopped_limit"] else "stop"

        time.sleep(1)

        return MirrorLiteLLMResponse(completion, finish_reason)
