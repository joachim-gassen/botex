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

    start_llama_server: bool = Field(default=False)
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
        if self.start_llama_server:
            if not self.path_to_llama_server:
                raise ValueError("You have indicated that you want botex to start the llama.cpp server, but you have not provided the path to the server.")
            if not self.local_llm_path:
                raise ValueError("You have indicated that you want botex to start the llama.cpp server, but you have not provided the path to the local language model.")
            if not os.path.exists(self.path_to_llama_server):
                raise FileNotFoundError(f"Server path {self.path_to_llama_server} not found.")
            if not os.path.exists(self.local_llm_path):
                raise FileNotFoundError(f"Model path {self.local_llm_path} not found.")
        return self
    


class LocalLLM:
    """
    A class to interact with the local language model server.

    Parameters:
    local_model_cfg (dict): A dictionary containing the configuration for the 
        local language model. The dictionary can contain any of the following keys:
        
        - start_llama_server (bool): Whether to start the llama cpp server, defaults to True. If False, the program will not start the server and will expect the server to be accessible under the URL provided by 'llama_server_url'.
        - path_to_llama_server (str): The path to the llama cpp server executable.
        - local_llm_path (str): The path to the local language model.
        - llama_server_url (str): The base URL for the llama cpp server, defaults to "http://localhost:8080".
        - context_length (int): The context length for the model, defaults to None. If None, the program will try to get the context length from the local model metadata, if that is not possible defaults to 4096.
        - number_of_layers_to_offload_to_gpu (int): The number of layers to offload to the GPU, defaults to 0.
        - temperature (float): The temperature for the model, defaults to 0.5.
        - maximum_tokens_to_predict (int): The maximum number of tokens to predict, defaults to 10000.
        - top_p (float): The top p value for the model, defaults to 0.9.
        - top_k (int): The top k value for the model, defaults to 40.
        - num_slots (int): The number of slots for the model, defaults to 1.
    
        For all the keys, if not provided, the program will try to get the value from environment variables (in all capital letters), if that is not possible, it will use the default value.
    """
    def __init__(self, local_model_cfg: dict):
        self.cfg = LocalLLMConfig(**local_model_cfg)
        
        self.start_llama_server = self.cfg.start_llama_server
        self.llama_server_url = self.cfg.llama_server_url
        
        self.top_p = self.cfg.top_p
        self.temperature = self.cfg.temperature
        self.top_k = self.cfg.top_k

        if self.start_llama_server:
            self.path_to_llama_server = self.cfg.path_to_llama_server
            self.local_llm_path = self.cfg.local_llm_path
            parsed_gguf = GGUFParser(self.local_llm_path)
            self.metadata = parsed_gguf.get_metadata()
            self.ngl = self.cfg.number_of_layers_to_offload_to_gpu
            self.c = int(self.cfg.context_length or self.metadata.get("context_length", 4096))
            self.n = self.cfg.maximum_tokens_to_predict
            self.num_slots = self.cfg.num_slots
        else:
            self.set_params_from_running_api()

    def __str__(self):
        return self.cfg.model_dump_json()


    def set_params_from_running_api(self) -> None:
        url = f"{self.llama_server_url}/props"
      
        try:
            response = requests.get(url)
            if response.status_code != 200:
                raise Exception(
                    "An error occurred while trying to get metadata from the running API. Are you sure you are running llama.cpp server and the llama_server_url is correct?"
                )
            res = response.json()
        except requests.ConnectionError:
            raise Exception(
                "An error occurred while trying to connect to your running llama.cpp server. Are you sure you are running llama.cpp server and the llama_server_url is correct?"
            )   
        try:
            self.local_llm_path = res['default_generation_settings']['model']
            self.c = res['default_generation_settings']['n_ctx']
            self.num_slots = res['total_slots']
            self.n = res['default_generation_settings']['n_predict']

            self.cfg = LocalLLMConfig(
                start_llama_server = False,
                llama_server_url = self.llama_server_url,
                local_llm_path = self.local_llm_path,
                context_length = self.c,
                number_of_layers_to_offload_to_gpu = None,
                temperature = self.temperature,
                maximum_tokens_to_predict = self.n,
                top_p = self.top_p,
                top_k = self.top_k,
                num_slots = self.num_slots
            )
        except KeyError as e:
            raise Exception("An error occurred while trying to get metadata, %s from the running API. Are you sure you are running llama.cpp server and the llama_server_url is correct? If so, please consider raising an issue on github." % e)

    def start_server(self):
        """
        Starts the local language model server.
        """
        parsed_url = urlparse(self.llama_server_url)
        if not self.start_llama_server:
            if self.is_server_reachable(parsed_url.hostname, parsed_url.port):
                logging.info("You have chosen to use an already running llama.cpp server. The server is running on %s and is reachable.", self.llama_server_url)
                return None
            raise Exception(f"You have chosen to use an already running llama.cpp server but the server is not reachable. Please make sure that llama.cpp server is up and running on llama_server_url: {self.llama_server_url}")

        if self.is_server_reachable(parsed_url.hostname, parsed_url.port, timeout=0):
            raise Exception("llama.cpp server is already running on %s, but you have indicated that you want botex to start the llama.cpp server. Please stop the server manually if you want botex to start the server or set start_llama_server to Fasle to work with an already running llama.cpp server.", self.llama_server_url)

        cmd = [
            self.path_to_llama_server,
            "--host",
            parsed_url.hostname,
            "--port",
            str(parsed_url.port),
            "-ngl",
            str(self.ngl),
            "-m",
            self.local_llm_path,
            "-c",
            str(int(self.num_slots) * (int(self.c) + int(self.n))),
            "-n",
            str(self.n),
            "--parallel",
            str(self.num_slots),
            "-fa",
        ]
        logging.info("Starting llama.cpp server ...")
        with open("llama_cpp_server.log", "a") as log_file:
            process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)

        if self.is_server_reachable(parsed_url.hostname, parsed_url.port):
            logging.info("llama.cpp server started successfully.")
            return process

        _, stderr = process.communicate(timeout=10)
        if process.returncode != 0 and stderr:
            logging.error("Failed to start llama.cpp server.")
            if "cudaMalloc failed: out of memory" in stderr.decode("utf-8"):
                raise Exception(
                    f"Failed to start llama.cpp server. Your model {self.local_llm_path} is too large for the available GPU memory. Please try a smaller model or decrease the number of layers, {self.ngl} that are offloaded to the GPU."
                )
            raise Exception(
                f"Failed to start llama.cpp server. Error: {stderr.decode('utf-8')}"
            )

        if self.is_server_reachable(parsed_url.hostname, parsed_url.port):
            logging.info("llama.cpp server started successfully.")
            return process
        else:
            logging.error("Failed to start llama.cpp server.")
            process.terminate()
            return None

    def is_server_reachable(self, host, port, timeout=60):
        """
        Waits for the server to become responsive.
        """
        url = f"http://{host}:{port}/health"
        start_time = time.time()
        while True:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    return True
            except requests.ConnectionError:
                if time.time() - start_time > timeout: return False 
                time.sleep(1)

    def stop_server(self, process: subprocess.Popen | None):
        """
        Stops the local language model server.
        """
        if not self.start_llama_server:
            logging.info("Externally started llama.cpp will not be terminated. Please stop it manually if appropriate.")
            return
        if process:
            logging.info("Stopping llama.cpp server...")
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()

            process.wait()
            logging.info("llama.cpp server stopped.")
        else:
            logging.warning("llama.cpp server is not running.")

    def completion(self, messages, response_format) -> ChatCompletionResponse:
        """
        Generates a completion for the given messages.

        Parameters:
        messages (list): A list of messages to generate the completion for.
        """

        url = f"{self.llama_server_url}/v1/chat/completions"

        payload = {
            "messages": messages,
            "temperature": self.temperature,
            "cache_prompt": False,
            "max_tokens": self.n,
            "response_format":  {
                "type": "json_object",
                "schema": response_format.model_json_schema()
            },
            "top_p": self.top_p,
            "top_k": self.top_k,
        }

        attempts = 0
        while True:
            try:
                response = requests.post(url, json=payload, timeout=900)
                break
            except Exception as e:
                logging.error(f"Error getting a response from local llm server: {e}. Retrying... (Attempt {attempts + 1}/3)")
                attempts += 1
                if attempts == 3:
                    raise Exception("Request timed out after 3 attempts.")

        if response.status_code != 200:
            raise Exception(
                f"An error occurred while generating the completion: {response.text}"
            )
        
        try:
            res = response.json()
            # Unfortunately, the response from llama.cpp is not correct here, this is a known issue on llama.cpp and there is a PR to fix it.
            logging.info(f"Total tokens used: {res['usage']['total_tokens']}")
            if res.get('usage') and res['usage']['completion_tokens'] >= self.n:
                res['choices'][0]['finish_reason'] = "length"
            return ChatCompletionResponse(**res)
        except ValidationError as e:
            error_log = "An error occurred while parsing the response. This is most likely because the local llm server is not responding with an OpenAI compliant JSON. Here is the error and response text:\n %s \n %s" % (e, response.text)
            logging.error(error_log)
            raise Exception(error_log)
