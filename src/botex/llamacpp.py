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

logger = logging.getLogger("botex")

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

class LlamaCppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLAMACPP_", env_ignore_empty=True)
    server_url: str = Field(default='http://localhost:8080')
    server_path: str | None = Field(default=None)
    local_llm_path: str | None = Field(default=None)
    context_length: int | None = Field(default=None)
    number_of_layers_to_offload_to_gpu: int = Field(default=0)
    temperature: float = Field(default=0.8)
    maximum_tokens_to_predict: int = Field(default=10000)
    top_p: float = Field(default=0.9)
    top_k: int = Field(default=40)
    num_slots: int = Field(default=1)

    @model_validator(mode='after')
    def check_required_fields(self):
        if not self.server_path:
            raise ValueError(
                "You have indicated that you want botex to start the "  
                "llama.cpp server, but you have not provided the path to "  
                "the server."
            )
        if not self.local_llm_path:
            raise ValueError(
                "You have indicated that you want botex to start the "  
                "llama.cpp server, but you have not provided the path to "  
                "the local language model."
            )
        if not os.path.exists(self.server_path):
            raise FileNotFoundError(
                f"Server path {self.server_path} not found."
            )
        if not os.path.exists(self.local_llm_path):
            raise FileNotFoundError(
                f"Model path {self.local_llm_path} not found."
            )
        if not self.context_length:
            self.context_length = GGUFParser(
                self.local_llm_path
            ).get_metadata().get("context_length", 4096)
        return self
    

def is_llamacpp_server_reachable(url, timeout=6):
    """
    Checks if the llama.cpp server at the given host and port is reachable.
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
        self.config = LlamaCppConfig(**config)

    def start_server(self) -> subprocess.Popen:
        if is_llamacpp_server_reachable(self.config.server_url):
            raise Exception(
                "A llama.cpp server is already running at " 
                f"{self.config.server_url}. "
                "Please stop it manually or use it directly."
            )

        parsed_url = urlparse(self.config.server_url)
        assert self.config.context_length, "Context length should have been set by now."
        cmd = [
            self.config.server_path,
            "--host", parsed_url.hostname,
            "--port", str(parsed_url.port),
            "-ngl", str(self.config.number_of_layers_to_offload_to_gpu),
            "-m", self.config.local_llm_path,
            "-c", str(int(self.config.num_slots) * self.config.context_length),
            "-n", str(self.config.maximum_tokens_to_predict),
            "--parallel", str(self.config.num_slots),
            "-fa",
        ]

        logger.info(
            f"Starting llama.cpp server '{self.config.server_path} "
            f"with model '{self.config.local_llm_path}' "
            f"listening to {self.config.server_url}... "
        )
        # Should the log file path become a configurable option at some point?
        with open("llama.log", "a") as log_file:
            process = subprocess.Popen(
                cmd, stdout=log_file, stderr=subprocess.STDOUT
            )

        if not is_llamacpp_server_reachable(self.config.server_url):
            self.terminate_process(process)
            raise Exception(
                "Failed to start llama.cpp server. Check the logs for details."
            )

        logger.info(
            "llama.cpp server started successfully. "
            "Logging output to llama_cpp_server.log"
        )
        return process

        
    @staticmethod
    def stop_server(process: subprocess.Popen):
        if process:
            logger.info("Stopping llama.cpp server...")
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()
            process.wait()
            logger.info("llama.cpp server stopped.")
        else:
            logger.warning("No running llama.cpp server found to stop.")

    @staticmethod
    def terminate_process(process=None):
        if process:
            process.terminate()
            process.wait()


class LlamaCpp:
    """
    A class to interact with the llama.cpp server.

    Parameters:
    api_base (str): The base URL of the llama.cpp server. This should include 
        the protocol (http/https) and domain/host (e.g., "http://localhost:8080").
    """
    def __init__(self, api_base: str | None = "http://localhost:8080"):
        if not api_base:
            api_base = "http://localhost:8080"
        self.api_base = api_base.rstrip("/")
        if not is_llamacpp_server_reachable(self.api_base):
            raise Exception(
                f"Cannot connect to llama.cpp server at {self.api_base}." 
                "Please ensure the server is running."
            )
        # Fetch metadata from the server
        self.set_params_from_running_api()

    def set_params_from_running_api(self):
        url = f"{self.api_base}/props"
        try:
            response = requests.get(url)
            response.raise_for_status()
            res = response.json()
            if "model_path" in res:
                self.local_llm_path = res['model_path']
            elif "model" in res['default_generation_settings']:
                self.local_llm_path = res['default_generation_settings']['model']
            else:
                logger.warning(
                    "Unable to determine the model path from the running llama" " server. Botex can function without the model path, but "
                    "you should consider updating your llama.cpp."
                )
                self.local_llm_path = "unknown"

            self.context_length = res['default_generation_settings']['n_ctx']
            self.num_slots = res['total_slots']
            if 'n_predict' in res['default_generation_settings']:
                self.max_tokens = res['default_generation_settings']['n_predict']
            else:    
                self.max_tokens = res['default_generation_settings']['params']['n_predict']
            self.temperature = 0.8
            self.top_p = 0.9
            self.top_k = 40
        except requests.RequestException as req_exc:
            raise Exception(
                "Failed to retrieve metadata from llama.cpp server "
                f"at {self.api_base}: {req_exc}"
            )
        except KeyError as key_err:
            raise Exception(
                "Failed to parse metadata from llama.cpp server, please "
                "consider raising an issue on the botex GitHub repository. "
                "Please provide your llama.cpp version and the error: "
                f"'{key_err}'"
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
        Generates a llama.cpp completion for the given messages.

        Parameters:
        messages (list): A list of messages to generate the completion for.
        response_format (PydanticModel): A Pydantic schema for the expected 
            response format.

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
                logger.error(
                    f"Error getting a response: {e}. Retrying... ({attempts}/3)"
                )
                if attempts == 3:
                    raise Exception("Request failed after 3 attempts.")

def start_llamacpp_server(config: dict | None = None) -> subprocess.Popen:
    """
    Starts a llama.cpp server instance.

    Args:
        config (dict | None, optional): A dict containing to the least
            the keys `llamacpp_server_path` (the path to the llama.cpp 
            executable) and `local_llm_path` (the path to the LLM model that you
            want llama.cpp to use). If None (the default), then these parameters
            are read from the environment variables `LLAMACPP_SERVER_PATH` and 
            `LLAMACPP_LOCAL_LLM_PATH`. See notes below for additional
            configuration parameters

    Returns:
        The process of the running llama.cpp sever if start was
            successful.

    Raises:
        Exception: If the server is already running or if starting the server 
            fails.            

    ??? tip "Additional details"
        You can provide other configuration parameters for the 
        local model in the model configuration dictionary. These include:

            -   `server_url` (str): The base URL for the llama.cpp 
                server, defaults to `"http://localhost:8080"`.

            -   `context_length` (int): The context length for the model. 
                If `None`, BotEx will try to get the context length from the 
                local model metadata; if that is not possible, it defaults 
                to `4096`.

            -   `number_of_layers_to_offload_to_gpu` (int): The number of 
                layers to offload to the GPU, defaults to `0`.

            - ` temperature` (float): The temperature for the model, 
                defaults to `0.5`.

            -   `maximum_tokens_to_predict` (int): The maximum number of 
                tokens to predict, defaults to `10000`.

            -   `top_p` (float): The top-p value for the model, 
                defaults to `0.9`.

            -   `top_k` (int): The top-k value for the model, 
                defaults to `40`.

            -   `num_slots` (int): The number of slots for the model, 
                defaults to `1`.


        For all these keys, if not provided in the configuration dictionary, 
        botex will try to get the value from environment variables (in all 
        capital letters, prefixed by LLAMACPP_); if that is not possible, it 
        will use the default value.
    

    ??? example "Example"
        ```python
        from botex.llamacpp import start_llamacpp_server

        config = {
            "server_path": "/path/to/llama.cpp",
            "local_llm_path": "/path/to/local/model",
            "server_url": "http://localhost:8080",
            "context_length": 4096,
            "number_of_layers_to_offload_to_gpu": 0,
            "temperature": 0.8,
            "maximum_tokens_to_predict": 10000,
            "top_p": 0.9,
            "top_k": 40,
            "num_slots": 1
        }
        ```
    """
    manager = LlamaCppServerManager(config)
    return manager.start_server()

def stop_llamacpp_server(process: subprocess.Popen) -> None:
    """
    Stops a running llama.cpp server instance.

    Args:
        process (subprocess.Popen): The process of the running llama.cpp server.

    Returns:
        None (stops the running llama.cpp server)
    """
    LlamaCppServerManager.stop_server(process)