import logging
import os
import psutil
import requests
import subprocess
import time
from urllib.parse import urlparse

from .gguf_parser import GGUFParser


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
    A class to interact with the local language model server.

    Parameters:
    start_llama_server (bool): Whether to start the llama cpp server, defaults 
        to True. If False, the program will not start the server and will 
        expect the server to be accessible under the URL provided by 
        'llama_server_url'.
    path_to_llama_server (str): The path to the llama cpp server executable.
    local_llm_path (str): The path to the local language model.
    llama_server_url (str): The base URL for the llama cpp server.
    context_length (int): The context length for the model, defaults to None.
        If None, the program will try to get the context length from the local
        model metadata, if that is not possible defaults to 4096.
    number_of_layers_to_offload_to_gpu (int): The number of layers to offload 
        to the GPU, defaults to 0.
    temperature (float): The temperature for the model, defaults to 0.5.
    top_p (float): The top p value for the model, defaults to 0.9.
    top_k (int): The top k value for the model, defaults to 40.
    num_slots (int): The number of slots for the model, defaults to 1.
    """

    def __init__(
        self,
        start_llama_server: bool = True,
        path_to_llama_server: str | None = None,
        local_llm_path: str | None = None,
        llama_server_url: str = "http://localhost:8080",
        context_length: int | None = None,
        number_of_layers_to_offload_to_gpu: int = 0,
        temperature: float = 0.5,
        maximum_tokens_to_predict: int = 10000,
        top_p: float = 0.9,
        top_k: int = 40,
        num_slots: int = 1,
        **kwargs,
    ):
        self.start_llama_server = start_llama_server
        self.llama_server_url = llama_server_url
        if start_llama_server:
            if path_to_llama_server is None:
                raise ValueError("You have indicated that you want botex to start the llama.cpp server, but you have not provided the path to the server.")
            else:
                self.server_path = path_to_llama_server
            if local_llm_path is None:
                raise ValueError("You have indicated that you want botex to start the llama.cpp server, but you have not provided the path to the local language model.")
            else:
                self.model_path = local_llm_path
            parsed_gguf = GGUFParser(self.model_path)
            self.metadata = parsed_gguf.get_metadata()
            self.ngl = int(number_of_layers_to_offload_to_gpu)
            self.c = (
                int(context_length)
                if context_length
                else self.metadata.get("context_length", 4096)
            )
            self.temperature = float(temperature)
            self.n = int(maximum_tokens_to_predict)
            self.top_p = float(top_p)
            self.top_k = int(top_k)
            self.num_slots = num_slots
        else:
            self.set_params_from_running_api()

    def set_params_from_running_api(self) -> None:
        url = f"{self.llama_server_url}/slots"
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
            self.model_path = res[0]['model']
            self.c = res[0]['n_ctx']
            self.temperature = round(res[0]['temperature'], 2)
            self.n = res[0]['n_predict']
            self.top_p = round(res[0]['top_p'], 2)
            self.top_k = res[0]['top_k']
            self.num_slots = len(res)
        except KeyError as e:
            raise Exception("An error occurred while trying to get metadata, %s from the running API. Are you sure you are running llama.cpp server and the llama_server_url is correct? If so, please consider raising an issue on github." % e)

    def validate_parameters(self):
        if not os.path.exists(self.server_path):
            raise FileNotFoundError(f"Server path not found: {self.server_path}")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model path not found: {self.model_path}")

    def start_server(self):
        """
        Starts the local language model server.
        """
        parsed_url = urlparse(self.llama_server_url)
        if not self.start_llama_server:
            if self.wait_for_server(parsed_url.hostname, parsed_url.port):
                logging.info("You have chosen to use an already running llama.cpp server. llama.cpp server is running on %s. Make sure this is what you intended", self.llama_server_url)
            else:
                raise Exception(f"You have chosen to use an already running llama.cpp server but the server is not reachable. Please make sure that llama.cpp server is up and running on llama_server_url: {self.llama_server_url}")
            return
        self.validate_parameters()

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
        logging.info(f"Starting llama.cpp server ...")
        with open("llama_cpp_server.log", "a") as log_file:
            process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)

        if self.wait_for_server(parsed_url.hostname, parsed_url.port):
            logging.info("llama.cpp server started successfully.")
            return process

        _, stderr = process.communicate(timeout=10)
        if process.returncode != 0 and stderr:
            logging.error("Failed to start llama.cpp server.")
            if "cudaMalloc failed: out of memory" in stderr.decode("utf-8"):
                raise Exception(
                    f"Failed to start llama.cpp server. Your model {self.model_path} is too large for the available GPU memory. Please try a smaller model or decrease the number of layers, {self.ngl} that are offloaded to the GPU."
                )
            raise Exception(
                f"Failed to start llama.cpp server. Error: {stderr.decode('utf-8')}"
            )

        if self.wait_for_server(parsed_url.hostname, parsed_url.port):
            logging.info("llama.cpp server started successfully.")
            return process
        else:
            logging.error("Failed to start llama.cpp server.")
            process.terminate()
            return None

    def wait_for_server(self, host, port, timeout=30):
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

    def completion(self, messages) -> MirrorLiteLLMResponse:
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
            "response_format": {"type": "json_object"},
            "top_p": self.top_p,
            "top_k": self.top_k,
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

        completion = response.json()["choices"][0]["message"]["content"]
        finish_reason = response.json()["choices"][0]["finish_reason"]

        return MirrorLiteLLMResponse(completion, finish_reason)
