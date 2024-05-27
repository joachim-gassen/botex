def assert_is_not_none(value):
    """Asserts that a value is not None.

    :param value: The value to check.
    :raises AssertionError: If `value` is None.
    """
    assert value is not None, f"{value} must be provided."


class LocalModelConfig(dict):
    """
    Configuration for a local model including paths and operational parameters.

    :param model_path: Path to the model directory.
    :param has_system_role: Flag indicating if the model includes a system role.
    :param number_of_layers_to_offload_to_gpu: Number of layers to offload to GPU for performance.
    :param context_length: The length of the context used by the model.
    :param temperature: The sampling temperature.
    :param max_num_of_tokens_to_generate: Maximum number of tokens the model is allowed to generate.
    :param top_p: The top probability cutoff for nucleus sampling.
    :param top_k: The top k cutoff for top-k sampling.
    """

    model_path: str
    has_system_role: bool
    number_of_layers_to_offload_to_gpu: int
    context_length: int
    temperature: float
    max_num_of_tokens_to_generate: int
    top_p: float
    top_k: int

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._assert_required_params()

    def _assert_required_params(self):
        """Asserts that all necessary parameters are provided."""
        for key in self.keys():
            assert_is_not_none(self[key])


class LLMConfig(dict):
    """
    Configuration for language model, supporting both local and remote models.

    :param model: Type of model ('local' or 'remote').
    :param system_prompt: Initial prompt for the model.
    :param system_prompt_few_shot_examples: Examples to prime the model.
    :param path_to_compiled_llama_cpp_main_file: Path to the compiled LLaMA binary file.
    :param local_model_cfg: Configuration for a local model if 'model' is 'local'.
    :raises ValueError: If 'model' is 'local' but 'local_model_cfg' is not provided.
    """

    model: str
    system_prompt: str
    system_prompt_few_shot_examples: str
    path_to_compiled_llama_cpp_main_file: str
    local_model_cfg: LocalModelConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert_is_not_none(self["model"])
        assert_is_not_none(self["system_prompt"])
        if self["model"] == "local":
            try:
                self["local_model_cfg"]
            except KeyError:
                raise ValueError("If model is local, local_llm_cfg must be provided.")
        LocalModelConfig(**self["local_model_cfg"])


class PromptsConfig(dict):
    """
    Stores templates for various prompts used in messaging within the system.

    :param start: Initial prompt for starting the interaction.
    :param analyze_page_no_q_full_hist: Prompt for analyzing a page without questions, using full history.
    :param analyze_page_q_full_hist: Prompt for analyzing a page with questions, using full history.
    :param analyze_first_page_no_q: Prompt for analyzing the first page without questions.
    :param analyze_page_no_q: Prompt for analyzing any page without questions.
    :param analyze_first_page_q: Prompt for analyzing the first page with questions.
    :param analyze_page_q: Prompt for analyzing a page with questions.
    :param end: Final prompt to end the interaction.
    :param json_error: Prompt when JSON parsing fails.
    :param confused: Prompt when the model is confused.
    :param resp_too_long: Prompt when the response is too long.
    :param page_not_changed: Prompt when the page has not changed.
    :param not_understood: Prompt when the input is not understood.
    :param no_summary: Prompt when there is no summary provided.
    :param no_questions: Prompt when no questions are present.
    :param questions_not_list: Prompt when questions are not in a list format.
    :param missing_keys_in_question: Prompt indicating missing keys in a question.
    """

    start: str
    analyze_page_no_q_full_hist: str
    analyze_page_q_full_hist: str
    analyze_first_page_no_q: str
    analyze_page_no_q: str
    analyze_first_page_q: str
    analyze_page_q: str
    end: str
    json_error: str
    confused: str
    resp_too_long: str
    page_not_changed: str
    not_understood: str
    no_summary: str
    no_questions: str
    questions_not_list: str
    missing_keys_in_question: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._assert_required_prompts()

    def _assert_required_prompts(self):
        """Asserts that all necessary prompts are provided."""
        for key in self.keys():
            assert_is_not_none(self[key])


class BotConfig(dict):
    """
    Configuration for a bot within the system, detailing database connections, interaction parameters, and prompts.

    :param botex_db: The database name for storing experiment data.
    :param full_conv_history: Flag to determine if the full conversation history should be used.
    :param otree_server_url: Base URL of the oTree server.
    :param otree_rest_key: REST API key for the oTree server.
    :param prompts: Configuration for the various prompts used by the bot.
    """

    botex_db: str
    full_conv_history: bool
    otree_server_url: str
    otree_rest_key: str
    prompts: PromptsConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self["prompts"], "Prompts must be provided."
        PromptsConfig(**self["prompts"])
