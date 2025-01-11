# botex: Using LLMs as Experimental Participants in oTree 

## Idea

This in-development Python package allows you to use large language models (LLMs) as bots in [oTree](https://www.otree.org) experiments. It has been inspired by recent work of Grossmann, Engel and Ockenfels ([paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4682602), [repo](https://github.com/mrpg/ego)) but uses a different approach. Instead of using dedicated prompts, botex bots consecutively scrape their respective oTree participant's webpage and infer the experimental flow solely from the webpage text content. This avoids the risk of misalignment between human (webpage) and bot (LLM prompt) experimental designs and, besides facilitating the study of LLM "behavior", allows to use LLM participants to develop and pre-test oTree experiments that are designed (primarily) for human participants.

The downside of this approach is that the scraping has to rely on some level of standardization. Luckily, the oTree framework is relatively rigid, unless the user adds customized HTML forms to their experimental designs. Currently, all standard form models used by oTree are tested and verified to work. In the future, we plan to implement also customized HTML forms but likely this will require some standardization by the user implementing the experimental design.

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


