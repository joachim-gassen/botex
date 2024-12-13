import logging
import os
import psutil
import requests
import subprocess
import time
from urllib.parse import urlparse

from .gguf_parser import GGUFParser

from pydantic import BaseModel, Field, model_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Message(BaseModel):
    role: str
    content: str

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str]

class Usage(BaseModel):
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    usage: Usage
    choices: List[Choice]

class LocalLLMConfig(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    llama_server_url: str = Field(default='http://localhost:8080')
    path_to_llama_server: str | None = Field(default=None)
    local_llm_path: str | None = Field(default=None)
    context_length: int | None = Field(default=None)
    number_of_layers_to_offload_to_gpu: int | None = Field(default=0)
    temperature: float = Field(default=0.8)
    maximum_tokens_to_predict: int = Field(default=10000)
    top_p: float = Field(default=0.9)
    top_k: int = Field(default=40)
    num_slots: int = Field(default=1)

    @model_validator(mode='after')
    def check_required_fields(self):
        if not self.path_to_llama_server:
            raise ValueError("You have indicated that you want botex to start the llama.cpp server, but you have not provided the path to the server.")
        if not self.local_llm_path:
            raise ValueError("You have indicated that you want botex to start the llama.cpp server, but you have not provided the path to the local language model.")
        if not os.path.exists(self.path_to_llama_server):
            raise FileNotFoundError(f"Server path {self.path_to_llama_server} not found.")
        if not os.path.exists(self.local_llm_path):
            raise FileNotFoundError(f"Model path {self.local_llm_path} not found.")
    

def is_llama_cpp_server_reachable(url, timeout=6):
    """
    Checks if the server at the given host and port is reachable.
    """

    url = f"{url}/health"
    start_time = time.time()
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except requests.ConnectionError:
            if time.time() - start_time > timeout:
                return False
            time.sleep(1)


class LlamaCppServerManager:
    def __init__(self, config: dict | None = None):
        config = config or {}
        self.config = LocalLLMConfig(**config)

    def start_server(self):
        if is_llama_cpp_server_reachable(self.config.llama_server_url):
            raise Exception(
                f"A llama.cpp server is already running at {self.config.llama_server_url}. "
                "Please stop it manually or use it directly."
            )

        parsed_url = urlparse(self.config.llama_server_url)
        cmd = [
            self.config.path_to_llama_server,
            "--host", parsed_url.hostname,
            "--port", str(parsed_url.port),
            "-ngl", str(self.config.number_of_layers_to_offload_to_gpu),
            "-m", self.config.local_llm_path,
            "-c", str(int(self.config.num_slots) * (int(self.config.context_length or 4096) + int(self.config.maximum_tokens_to_predict))),
            "-n", str(self.config.maximum_tokens_to_predict),
            "--parallel", str(self.config.num_slots),
            "-fa",
        ]

        logging.info("Starting llama.cpp server...")
        with open("llama_cpp_server.log", "a") as log_file:
            process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)

        if not is_llama_cpp_server_reachable(self.config.llama_server_url):
            self.terminate_process(process)
            raise Exception("Failed to start llama.cpp server. Check the logs for details.")

        logging.info("llama.cpp server started successfully.")

        return process

        
    @staticmethod
    def stop_server(process=None):
        if process:
            logging.info("Stopping llama.cpp server...")
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()
            process.wait()
            logging.info("llama.cpp server stopped.")
        else:
            logging.warning("No running llama.cpp server found to stop.")

    @staticmethod
    def terminate_process(process=None):
        if process:
            process.terminate()
            process.wait()


class LocalLLM:
    """
    A class to interact with the llama.cpp server.

    Parameters:
    api_base (str): The base URL of the llama.cpp server. This should include the protocol (http/https) 
        and domain/host (e.g., "http://localhost:8080").
    """
    def __init__(self, api_base: str | None = "http://localhost:8080"):
        if not api_base:
            api_base = "http://localhost:8080"
        self.api_base = api_base.rstrip("/")
        if not is_llama_cpp_server_reachable(self.api_base):
            raise Exception(f"Cannot connect to llama.cpp server at {self.api_base}. Please ensure the server is running.")

        # Fetch metadata from the server
        self.set_params_from_running_api()

    def set_params_from_running_api(self):
        url = f"{self.api_base}/props"
        try:
            response = requests.get(url)
            response.raise_for_status()
            res = response.json()
            self.local_llm_path = res['default_generation_settings']['model']
            self.context_length = res['default_generation_settings']['n_ctx']
            self.num_slots = res['total_slots']
            self.max_tokens = res['default_generation_settings']['n_predict']
            self.temperature = 0.8
            self.top_p = 0.9
            self.top_k = 40
        except (requests.RequestException, KeyError) as e:
            raise Exception(
                f"Failed to retrieve metadata from llama.cpp server at {self.api_base}: {e}"
            )

    def json_dump_model_cfg(self):
        return {
            "api_base": self.api_base,
            "model": self.local_llm_path,
            "context_length": self.context_length,
            "num_slots": self.num_slots,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
        }    
    

    def completion(self, messages, response_format=None) -> ChatCompletionResponse | None:
        """
        Generates a completion for the given messages.

        Parameters:
        messages (list): A list of messages to generate the completion for.
        response_format (PydanticModel): A Pydantic schema for the expected response format.

        Returns:
        ChatCompletionResponse: The completion response.
        """
        url = f"{self.api_base}/v1/chat/completions"

        payload = {
            "messages": messages,
            "temperature": self.temperature,
            "cache_prompt": False,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "top_k": self.top_k,
        }

        if response_format:
            payload["response_format"] = {
                "type": "json_object",
                "schema": response_format.model_json_schema()
            }

        attempts = 0
        while attempts < 3:
            try:
                response = requests.post(url, json=payload, timeout=900)
                response.raise_for_status()
                return ChatCompletionResponse(**response.json())
            except requests.RequestException as e:
                attempts += 1
                logging.error(f"Error getting a response: {e}. Retrying... ({attempts}/3)")
                if attempts == 3:
                    raise Exception("Request failed after 3 attempts.")

def start_llama_cpp_server(config: dict | None = None):
    manager = LlamaCppServerManager(config)
    return manager.start_server()

def stop_llama_cpp_server(process=None):
    LlamaCppServerManager.stop_server(process)