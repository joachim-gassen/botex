# botex: Using LLMs as Experimental Participants in oTree 

## Overview

Welcome to botex, a new Python package that leverages the power of **large language models (LLMs) as participants in oTree experiments**.

botex takes a novel approach to integrating LLMs into behavioral experiments. Rather than relying on predefined prompts,[^1] **botex bots dynamically interact with their experimental environment by scraping their respective oTree participant pages**. This approach allows them to infer the experimental flow solely from the webpage's textual content. By aligning bot behavior directly with the experimental interface, botex eliminates potential discrepancies between human and bot designs. This not only opens up **exciting opportunities to explore LLM behavior** but also positions LLMs as a **powerful tool for developing and pre-testing experiments** intended for human participants.

[^1]:  See, for example, Grossmann, Engel and Ockenfels ([paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4682602), [repo](https://github.com/mrpg/ego))

<p style="text-align: center;">
  <img src="assets/images/index_botex_workflow.svg" alt="botex Workflow" width="80%">
</p>

 For interfacing with LLMs, it offers two options

- [litellm](https://litellm.vercel.app): Allows the use of OpenAI's Chat-GPT AI and various other LLMs. 
- [llama.cpp](https://github.com/ggerganov/llama.cpp): Allows the use of local (open source) LLMs  

While both approaches have been tested and found to work, currently, we have only used OpenAI's Chat GPT-4 model for our own research work.


## Installation

If you want to use botex to create LLM participants for your own oTree experiments, you need the following:

- A working python environment >= 3.10 and preferable a virtual environment.
- [Google Chrome](https://www.google.com/chrome/) and [ChromeDriver](https://developer.chrome.com/docs/chromedriver/get-started) for scraping the oTree participant pages
- If you plan to use Chat-GPT 4 as your LLM (recommended for beginners), an [OpenAI API key](https://openai.com/api). If you want to go local, take a look at the next section.
- Access to an oTree server that you can start sessions on or at least an URL of an oTree participant link. The server can be local or remote.

Then install the botex package: `pip install botex==0.1.0`. 

## Running a bot on a single participant link

After that, you should be able to start botex on an existing oTree participant link by running the following code snippet

```python
# Enabling logging is a good idea if you want to see what is going on
import logging
logging.basicConfig(level=logging.INFO)

import botex

# Running a botex bot on a specific oTree participant link
botex.run_single_bot(
    botex_db = "path to a sqlite3 file that will store the bot data (does not need to exist)", 
    session_id = "The session ID of your oTree experiment (will be stored with the botex data)", 
    url = "the URL of the participant link", 
    openai_api_key = "your OpenAI api key"
)
```

## Initalizing an oTree session and starting bots

Alternatively, you can use botex to initialize a session on your oTree server and to start all required bots for the session in one go. This session can also contain human participants. However, in that case, you would be responsible to get the humans going to complete the session ;-)

```python
import logging
logging.basicConfig(level=logging.INFO)

import botex

# Initialize an oTree session
sdict = botex.init_otree_session(
    config_name = "config name of your oTree experiment", 
    npart = 6 # number of participants in the session, including bots and humans
    nhumans = 0, # set to non-zero if you want humans to play along
    botex_db = "path to a sqlite3 file (does not need to exist)",
    otree_server_url = "url of your server, e.g., http://localhost:8000]",
    otree_rest_key = "your oTree API secret key"
)

# The returned dict will contain the oTree session ID, all participant codes, 
# human indicators, and the URLs separately for the LLM and human participants.
# You can now start all LLM participants of the session in one go.  
botex.run_bots_on_session(
    session_id = sdict['session_id'],  
    botex_db = "same path that you used for initializing the session", 
    openai_api_key = "your OpenAI api key"
)
```

After the bots have completed their runs, you should have their response data stored in your oTree database just as it is the case for human participants. If you are interested in exploring the botex data itself, which is stored in the sqlite3 file that you provided, we recommend that you take a look at our botex case study.


## Use of local LLMs

If you want to use a local LLM instead of commercial APIs via the litellm interface you need, in addition to the above:

- llama.cpp. Clone it from [here](https://github.com/ggerganov/llama.cpp) and follow the instructions to build it.
- A local LLM model. You can use different models (e.g., from Hugging Face) but for starters download a GGUF-format model of [Mistral-7B-Instruct-v0.3.Q4_K_M.gguf](https://huggingface.co/MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF). At the moment the following [Q4_K_M version](https://huggingface.co/MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/Mistral-7B-Instruct-v0.3.Q4_K_M.gguf) is tested and working.

Then all that you need to do is to adjust the botex calls from above by specifying the model and its configuration. You do this by providing a `LocalLLM` object to the botex calls that start bots. For example, for `botex.run_bots_on_session()`, your call would look something like this

```python
botex.run_bots_on_session(
    session_id = sdict['session_id'],  
    botex_db = "same path that you used for initializing the session", 
    model = "local",
    local_model_cfg={
        "path_to_llama_server": "the path to the llama.cpp server (called llama-server or server on older versions)",
        "local_llm_path": "the path to your LLM model GGUF file"
    }
)
```

Everything else from above remains the same. When starting local LLMs as bots take a good look at the log files to see how they do.

## More information

If you want to learn more about botex you can read our [paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4891763).


## Get in touch!

If you are interested in this project or even have already tried it, we would love to hear from you. Simply shoot an email, comment on our linkedin post, or open an issue on GitHub!
