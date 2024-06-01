import logging
from jinja2 import Template
import json
import os
import re
import subprocess
from typing import List, Union, Iterable


class Message(dict):
    """
    Represents a generic message within a chat history.

    :param role: The role of the message sender ('user', 'assistant', or 'system').
    :param content: The textual content of the message.
    :raises ValueError: If content is empty or role is not one of the specified values.
    """

    def __init__(self, role: str, content: str) -> None:
        if isinstance(content, str) and content != "":
            super().__init__({"role": role, "content": content})
        else:
            raise ValueError("Content must be a non-empty string.")
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
        path_to_compiled_llama_cpp_main_file: str,
        local_model_path: str,
        system_prompt_few_shot_examples: ChatHistory | None = None,
        has_system_role: bool = False,
        ngl: int = 1,
        c: int = 32768,
        temp: float = 0,
        n: int = 10000,
        top_p: float = 0.9,
        top_k: int = 40,
    ):
        self.system_prompt_few_shot_examples = system_prompt_few_shot_examples
        self.main_path = path_to_compiled_llama_cpp_main_file
        self.model_path = local_model_path
        self.has_system_role = has_system_role
        self.ngl = ngl
        self.c = c
        self.temp = temp
        self.n = n
        self.top_p = top_p
        self.top_k = top_k

    def prepare_prompt(
        self,
        chat_history: ChatHistory,
        question: Union[HumanMessage, str] | None = None,
    ) -> None:
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
        model_folder = "/".join(self.model_path.split("/")[:-1])
        files = os.listdir(model_folder)
        if "tokenizer_config.json" not in files:
            raise FileNotFoundError(
                "No tokenizer found in the model path. Please ensure the model path is correct and that it has a tokenizer_config.json file."
            )
        with open(model_folder + "/tokenizer_config.json", "r") as f:
            token_config = json.load(f)
        self.start_token = token_config["bos_token"]
        self.end_token = token_config["eos_token"]

        # using Mistral 7b v3 instruct template as default
        default_chat_template = """
        {{ bos_token }}{% for message in messages %}{% if (message['role'] == 'user') != (loop.index0 % 2 == 0) %}{{ raise_exception('Conversation roles must alternate user/assistant/user/assistant/...') }}{% endif %}{% if message['role'] == 'user' %}{{ '[INST] ' + message['content'] + ' [/INST]' }}{% elif message['role'] == 'assistant' %}{{ message['content'] + eos_token}}{% else %}{{ raise_exception('Only user and assistant roles are supported!') }}{% endif %}{% endfor %}
        """

        if "chat_template" not in token_config:
            logging.warning(
                "No chat template found in the tokenizer config. Using default template from Mistral 7b v3 instruct. This might severely affect the model's performance. Also keep in mind there is no system role in the default template."
            )
            token_config["chat_template"] = default_chat_template
            self.has_system_role = False

        template = Template(token_config["chat_template"])

        if not self.has_system_role:
            messages = self.push_system_message_to_user(messages)

        return template.render(
            messages=messages, add_generation_prompt=True, **token_config
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

    def llm_setup(self, prompt) -> List[str]:
        """
        Sets up the command line arguments for running the local language model based on the current state and model configuration.

        :return: A list of command line arguments to execute the language model.
        """
        return [
            self.main_path,
            "-ngl",
            str(self.ngl),
            "-m",
            self.model_path,
            "-c",
            str(self.c),
            "--temp",
            str(self.temp),
            "--no-display-prompt",
            "--grammar-file",
            self.main_path.replace("/main", "/grammars/json.gbnf"),
            "-n",
            str(self.n),
            "--reverse_prompt",
            "\n\n\n\n\n\n\n\n\n\n\n\n\n\n",
            "--reverse_prompt",
            "\t\t\t\t\t\t\t\t\t\t\t\t\t\t",
            "--reverse_prompt",
            " \n  \n  \n  \n  \n  \n  \n  \n  ",
            "--top-p",
            str(self.top_p),
            "--top-k",
            str(self.top_k),
            "-p",
            prompt,  # type: ignore
        ]

    def completion(self, messages) -> MirrorLiteLLMResponse:
        """
        Generates a completion by setting up the prompt, running the local language model, and processing its output.

        :param question: The question to be answered by the model.
        :param chat_history: The current chat history for context.
        :return: A tuple containing the generated completion and the finish reason.
        :raises Exception: If there is an error during the execution of the model command.
        """
        prompt = self.prepare_prompt(messages)
        cmd = self.llm_setup(prompt)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(
                "There was an error running the command. The error was: %s"
                % result.stderr
            )

        match = re.search(
            r"sample time =\s*\d+,\d+\s*ms\s*/\s*(\d+)\s*runs", result.stderr
        )
        assert match is not None, "Could not find completion tokens in the output."
        completion_tokens = int(match.group(1))
        finish_reason = "stop" if completion_tokens < self.n else "length"

        completion = result.stdout.strip()

        completion = completion.replace(self.start_token, "").replace(
            self.end_token, ""
        )

        # hacky
        if "Llama-3" in self.model_path:
            completion = completion.replace("<|eot_id|>", "")

        # hacky
        if "Phi-3" in self.model_path:
            completion = completion.replace("<|end|>", "")

        return MirrorLiteLLMResponse(completion, finish_reason)
