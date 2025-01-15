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

import instructor
from instructor.exceptions import InstructorRetryException

from random import random
import time



instructor_client = instructor.from_litellm(litellm.completion)

def model_supports_response_schema(
        model: str, custom_llm_provider: str = None
    ) -> bool:
    """
    Check if litellm supports response schema for a given model string.

    Args:
        model (str): The model name.
        custom_llm_provider (str): The custom LLM provider, extracted from model str if missing.

    Returns:
        bool: True if the model supports response schema, False otherwise.
    """
    if model == "llamacpp": return True 
    if custom_llm_provider is None or not custom_llm_provider:
        if "/" not in model:
            custom_llm_provider = "openai"
        else:
            custom_llm_provider = model.split("/")[0]
    params = litellm.get_supported_openai_params(
        model=model, custom_llm_provider=custom_llm_provider
    )
    if "response_format" not in params:
        return False

    return litellm.supports_response_schema(
        model=model, custom_llm_provider=custom_llm_provider
    )

def log_completion_response(response) -> None:
    print("## Completion response:")
    print(response.model_dump())

instructor_client.on("completion:response", log_completion_response)

def instructor_completion(**kwargs):
    """
    Wrapper function for instructor client completion.

    Args:
        **kwargs: The keyword arguments.

    Returns:
        dict: The response JSON string and finish reason.
    """
    response_format = kwargs.pop("response_format")
    kwargs.pop("throttle", None)
    try:
        resp_instructor = instructor_client.chat.completions.create(
            response_model=response_format,
            max_tokens=131071,
            **kwargs
        )
    except InstructorRetryException as e:
        logger.warning(f"Instructor Retry Exception after {e.n_attempts} attempts")
        logger.warning(f"Last completion: {e.last_completion}")
        logger.warning(f"Error: {e.messages[-1]['content']}")
        raise(e)
    resp = {
        'resp_str': resp_instructor.model_dump_json(),
        'finish_reason': 'stop'
    }
    return resp

def litellm_completion(**kwargs):
    """
    Wrapper function for LiteLLM completion.

    Args:
        **kwargs: The keyword arguments.

    Returns:
        dict: The response JSON string and finish reason.
    """
    if not kwargs.get("throttle"):
        try:
            resp_litellm = litellm.completion(**kwargs)
        except Exception as e:
            logger.warning(f"Litellm completion failed, error: '{e}'")
            logger.info("Retrying with throttling.")
            kwargs["throttle"] = True
            return litellm_completion_with_backoff(**kwargs)
    else:
        kwargs.pop("throttle", None)
        resp_litellm = litellm.completion(**kwargs)
    resp = {
        'resp_str': resp_litellm.choices[0].message.content,
        'finish_reason': resp_litellm.choices[0].finish_reason
    }
    return resp

def llamacpp_completion(**kwargs):
    """
    Wrapper function for llama.cpp completion.

    Args:
        **kwargs: The keyword arguments.

    Returns:
        dict: The response JSON string and finish reason.
    """

    llamacpp = kwargs.get("llamacpp")
    messages = kwargs.get("messages")
    response_format = kwargs.get("response_format")
    resp_llamacpp = llamacpp.completion(messages, response_format)
    resp = {
        'resp_str': resp_llamacpp.choices[0].message.content,
        'finish_reason': resp_llamacpp.choices[0].finish_reason
    }
    return resp


def retry_with_exponential_backoff(
    func,
    wait_before_request_min: float = 0,
    wait_before_request_max: float = 5,
    minimum_backoff: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 100
):
    def wrapper(*args, **kwargs):
        num_retries = 0
        delay = minimum_backoff

        while True:
            try:
                wait_before = wait_before_request_min + \
                    (wait_before_request_max-wait_before_request_min) *\
                    random()
                if wait_before > 0 and num_retries == 0:
                    logger.info(
                        f"Throttling: Waiting for {wait_before:.1f} " + 
                        "seconds before sending completion request."
                    )
                    time.sleep(wait_before)
                return func(*args, **kwargs)

            except Exception as e:
                num_retries += 1
                if num_retries > max_retries:
                    raise Exception(
                        "Throttling: Maximum number of retries " + 
                        f"({max_retries}) exceeded."
                    )
                delay *= exponential_base * (1 + jitter * random())
                logger.info(
                    f"Throttling: Request error: '{e}'. "+ 
                    f"Retrying in {delay:.2f} seconds."
                )
                time.sleep(delay)

    return wrapper

@retry_with_exponential_backoff
def litellm_completion_with_backoff(**kwargs):
    return litellm_completion(**kwargs)

@retry_with_exponential_backoff
def instructor_completion_with_backoff(**kwargs):
    return instructor_completion(**kwargs)

def completion(**kwargs):
    model = kwargs.get("model")

    if model == "llamacpp":
        kwargs.pop("throttle", None)
        return llamacpp_completion(**kwargs)
    
    kwargs.pop("llamacpp", None)
    
    if model_supports_response_schema(model):
        if kwargs.get("throttle"):
            return litellm_completion_with_backoff(
                num_retries = 0, max_retries = 0, **kwargs
            )
        else:
            kwargs.pop("throttle", None)
            return litellm_completion(**kwargs)
    else:
        if kwargs.get("throttle"):
            return instructor_completion_with_backoff(
                num_retries = 0, max_retries = 0, **kwargs
            )
        else:
            kwargs.pop("throttle", None)
            return instructor_completion(**kwargs)

