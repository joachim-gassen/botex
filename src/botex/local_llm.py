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
    path_to_llama_server (str): The path to the llama cpp server executable.
    local_llm_path (str): The path to the local language model.
    start_llama_server (bool): Whether to start the llama cpp server, defaults to True. If False, the program will not start the server and will expect the server to be started manually by the user.
    api_base_url (str): The base URL for the llama cpp server.
    context_length (int): The context length for the model, defaults to None.
        If None, the program will try to get the context length from the local
        model metadata, if that is not possible defaults to 4096.
    number_of_layers_to_offload_to_gpu (int): The number of layers to offload to the GPU.
    temperature (float): The temperature for the model, defaults to 0.5.
    top_p (float): The top p value for the model, defaults to 0.9.
    top_k (int): The top k value for the model, defaults to 40.
    """

    def __init__(
        self,
        path_to_llama_server: str,
        local_llm_path: str,
        start_llama_server: bool = True,
        api_base_url: str = "http://localhost:8080",
        context_length: int | None = None,
        number_of_layers_to_offload_to_gpu: int = 1,
        temperature: float = 0.5,
        maximum_tokens_to_predict: int = 10000,
        top_p: float = 0.9,
        top_k: int = 40,
        num_slots: int = 1,
        **kwargs,
    ):
        self.server_path = path_to_llama_server
        self.model_path = local_llm_path
        self.start_llama_server = start_llama_server
        self.api_base_url = api_base_url
        parsed_gguf = GGUFParser(self.model_path)
        self.metadata = parsed_gguf.get_metadata()
        self.ngl = int(number_of_layers_to_offload_to_gpu)
        self.c = (
            int(context_length)
            if context_length
            else self.metadata.get("context_length", 4096)
        )
        self.temp = float(temperature)
        self.n = int(maximum_tokens_to_predict)
        self.top_p = float(top_p)
        self.top_k = int(top_k)
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
        if not self.start_llama_server:
            logging.info("You have chosen to manually start the LLM server. Please make sure that llama_server is up and running on %s", self.api_base_url)
            return
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

    def stop_server(self, process: subprocess.Popen | None):
        """
        Stops the local language model server.
        """
        if not self.start_llama_server:
            logging.info("The LLM server is started manually. Please stop it manually as well.")
            return
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

    def completion(self, messages) -> MirrorLiteLLMResponse:
        """
        Generates a completion for the given messages.

        Parameters:
        messages (list): A list of messages to generate the completion for.
        """

        url = f"{self.api_base_url}/v1/chat/completions"

        payload = {
            "messages": messages,
            "temperature": self.temp,
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
