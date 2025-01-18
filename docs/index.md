# botex: Using LLMs as Experimental Participants in oTree 

## Overview

Welcome to botex, a new Python package that leverages the power of **large language models (LLMs) as participants in oTree experiments**.

Botex takes a novel approach to integrating LLMs into behavioral experiments. Rather than relying on predefined prompts,[^1] **botex bots dynamically interact with their experimental environment by scraping their respective oTree participant pages**. This approach allows them to infer the experimental flow solely from the webpage's textual content. By aligning bot behavior directly with the experimental interface, botex eliminates potential discrepancies between human and bot designs. This not only opens up **exciting opportunities to explore LLM behavior** but also positions LLMs as a **powerful tool for developing and pre-testing experiments** intended for human participants.

[^1]:  See, for example, Grossmann, Engel and Ockenfels ([paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4682602), [repo](https://github.com/mrpg/ego))

<p style="text-align: center;">
  <img src="assets/images/index_botex_workflow.svg" alt="Botex Workflow" width="80%">
</p>

## Why Choose Botex?

botex's innovative approach offers several advantages:

- **Alignment**: By scraping oTree pages, LLMs respond to the same interface as human participants, ensuring consistency in experimental design.
- **Pre-testing**: LLMs can act as intelligent pre-testers, providing valuable feedback during the design phase of human-centric experiments.
- **Behavioral Insights**: Explore how LLMs interact and respond under experimental conditions designed for humans.

## Current Capabilities and Limitations

While botex provides robust functionality for standard oTree forms, its reliance on web scraping introduces certain constraints:

- **Standardized oTree Designs**: The oTree framework’s rigidity ensures compatibility, but customized HTML forms may require adjustments.
- **Future Enhancements**: We aim to extend support to custom HTML forms. However, some degree of standardization by users will likely be necessary for seamless integration.

See [Getting Started](getting_started.md) for a quick start guide.

## Usable LLMs

For interfacing with LLMs, botex offers two options

- [litellm](https://litellm.vercel.app): Allows the use of various commercial LLMs
- [llama.cpp](https://github.com/ggerganov/llama.cpp): Allows the use of local (open source) LLMs  

The model that you use for inference has to support [structured outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/). We have tested botex with the following LLMs:

| Vendor | Model | Link | Status | Notes |
| --- | --- | --- | --- | --- |
| OpenAI | gpt-4o-2024-08-06 and later | [OpenAI API](https://openai.com/api/) | OK | Requires at least paid user tier 1 |
| OpenAI |  gpt-4o-mini-2024-07-18 and later | [OpenAI API](https://openai.com/api/) | OK | Requires at least paid user tier 1  |
| Google | gemini/gemini-1.5-flash-8b | [Google AI Studio](https://ai.google.dev) | OK | 1,500 requests per day are free |
| Google | gemini/gemini-1.5-flash | [Google AI Studio](https://ai.google.dev) | OK | 1,500 requests per day are free |
| Google | gemini/gemini-1.5-pro | [Google AI Studio](https://ai.google.dev) | OK | 50 requests per day are free (not usable for larger experiments in the free tier) |
| Open Source | llama-3.1-8b-instruct-Q8_0.gguf | [Hugging Face](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | OK | Run with llama.cpp |
| Open Source | Mistral-7B-Instruct-v0.3.Q4_K_M.gguf | [Hugging Face](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3) | OK | Run with llama.cpp |
| Open Source | qwen2.5-7b-instruct-q4_k_m.gguf | [Hugging Face](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF)  | OK | Run with llama.cpp |


If you have success running botex with other models, please let us know so that we can add them to the list.

## Paper

If you use botex in your research, please cite its accompanying paper:

Fikir Worku Edossa, Joachim Gassen, and Victor S. Maas (2024): Using Large Language Models to Explore Contextualization Effects in Economics-Based Accounting Experiments. Working Paper. [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4891763).


