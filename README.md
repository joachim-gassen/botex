# botex: Using LLMs as Experimental Participants in oTree

## Idea

This in-development Python package allows you to use large language models (LLMs) as bots in [oTree](https://www.otree.org) experiments. For interfacing with LLMs, it offers two options

- [litellm](https://litellm.vercel.app): Allows the use of OpenAI's Chat-GPT AI and various other LLMs. 
- [llama.cpp](https://github.com/ggerganov/llama.cpp): Allows the use of local (open source) LLMs  

While both approaches have been tested and found to work, currently, we have only used OpenAI's Chat GPT-4 model for our own research work.

botex has been inspired by [recent work](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4682602) but uses a different approach. Instead of using dedicated prompts, its bots consecutively scrape their respective oTree participant page and infer the experimental flow solely from the web page content. This avoids the risk of misalignment between human (web page) and bot (LLM prompt) experimental designs and, besides facilitating the study of LLM "behavior", allows to use LLM participants to develop and pre-test oTree experiments that are designed (primarily) for human participants.

The downside of this approach is that the scraping has to rely on some level of standardization. Luckily, the oTree framework is relatively rigid, unless the user adds customized HTML forms to their experimental designs. Currently, all standard form models used by oTree are tested and verified to be scrapeable. In the future, we plan to implement also customized HTML forms but likely this will require some standardization by the user implementing the experimental design.


## Usage

If you want to use botex to create LLM participants for your own oTree experiments, you need the following:

- A working python environment >= 3.10 and preferable a virtual environment.
- [Google Chrome](https://www.google.com/chrome/) and [ChromeDriver](https://developer.chrome.com/docs/chromedriver/get-started) for scraping the oTree participant pages
- If you plan to use Chat-GPT 4 as your LLM (recommended for beginners), an [OpenAI API key](https://openai.com/api). If you want to go local, take a look at the next section.
- Access to an oTree server that you can start sessions on or at least an URL of an oTree participant link. The server can be local or remote.

Then install the botex package: `pip install botex`. After that, you should be able to start botex on an existing oTree participant link by running the following code snippet

```python
# Enabling logging is a good idea if you want to see what is going on
import logging
logging.basicConfig(level=logging.INFO)

import botex

# Running a botex bot on a specific oTree participant link
botex.run_bot(
    botex_db = "path to a sqlite3 file that will store the bot data (does not need to exist)", 
    session_id = "The session ID of your oTree experiment (will be stored with the botex data)", 
    url = "the URL of the participant link", 
    openai_api_key = "your OpenAI api key"
)
```

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
        "path_to_compiled_llama_server_executable": "the path to the llama.cpp server (called llama-server or server on older versions)",
        "local_model_path": "the path to your LLM model GGUF file"
    }
)
```

Everything else from above remains the same. When starting local LLMs as bots take a good look at the log files to see how they do.


## Installation for Development

If you want to take a deep-dive into botex and contribute to its development you can do the following

1. Clone this repository: `git clone https://github.com/joachim-gassen/botex` 
2. Copy `_secret.env` to `secret.env` and edit. Most importantly, you have to set your OpenAI key. As the otree instance will only be used for testing, you can set any password and rest key that you like.
3. Set up a virtural environment `python3 -m venv .venv`
4. Activate it `source .venv/bin/activate`
5. Install the necessary packages `pip install -r requirements.txt`
6. Install the botex package locally and editable `pip install -e .`
7. Test whether everything works `pytest --remote`
8. If you are using local LLMs, you need to provide the required configuration information in `secrets.env`. 
9. Then you should be able to test the local LLM config by running `pytest --local`
10. If you are interested in testing both the remote and local LLM you can run both tests with `pytest`.

If it works you should see a test output similar to this one:

```
=========================== test session starts ================================
platform darwin -- Python 3.12.2, pytest-8.1.1, pluggy-1.4.0
rootdir: /Users/joachim/github/botex
configfile: pyproject.toml
plugins: anyio-4.3.0, cov-4.1.0, dependency-0.6.0
collected 20 items                                                                                                                                                                          

tests/test_a_botex_db.py .
tests/test_b_otree.py ....
tests/test_c_local_llm.py ......
tests/test_c_openai.py ......
tests/test_d_exports.py ..

------------------------------ Local LLM answers -------------------------------
Question: What is your favorite color?'
Answer: 'blue'
Rationale: 'As a human, I perceive colors visually and my favorite color is blue.'.

Question: What is your favorite number?'
Answer: '7'
Rationale: 'I have no personal feelings towards numbers, but I will randomly select the number 7.'.

Question: Do you like ice cream?'
Answer: 'Yes'
Rationale: 'Yes, I do like ice cream.'.

Question: Which statement do you most agree with?'
Answer: 'Humans are better than bots'
Rationale: 'I believe that humans have unique qualities and capabilities that set them apart from bots, but I acknowledge that bots can be useful in many ways.'.

Question: What do you enjoy doing most?'
Answer: 'Reading'
Rationale: 'I chose the activity I enjoy most'.

Question: How many people live on the earth currently (in billions)?'
Answer: '7.9'
Rationale: 'I looked up the current population of Earth'.

Question: Do you have any feedback that you want to share?'
Answer: 'This survey was interesting and I hope it helps improve the functionality of the python package for Language Model Models to participate in oTree experiments.'
Rationale: 'I have feedback to share'.

------------------------------ OpenAI answers ----------------------------------
Question: What is your favorite color?'
Answer: 'Blue'
Rationale: 'Blue is generally calming and pleasant to me.'.

Question: What is your favorite number?'
Answer: '7'
Rationale: '7 is considered a lucky number in many cultures and it's always been my favorite.'.

Question: Do you like ice cream?'
Answer: 'Yes'
Rationale: 'I enjoy the taste and variety of flavors.'.

Question: Which statement do you most agree with?'
Answer: 'Humans are better than bots'
Rationale: 'As an AI, I recognize the value that both humans and bots bring, but I understand the statement that 'Humans are better than bots' as humans create and provide meaningful interpretations for information.'.

Question: What do you enjoy doing most?'
Answer: 'Reading'
Rationale: 'I enjoy reading because it allows me to learn new things and relax.'.

Question: How many people live on the earth currently (in billions)?'
Answer: '7.8'
Rationale: 'Based on current estimates, the global population is about 7.8 billion.'.

Question: Do you have any feedback that you want to share?'
Answer: 'This survey is well-structured and straightforward to follow.'
Rationale: 'Providing constructive feedback can improve future surveys.'.

==================== 20 passed in 192.76s (0:03:12) ============================
```

You see that it also contains some questions and answers. They are also accessible in `test/questions_and_answers.csv` after the run and were given by two bot instances in the oTree test survey `test/otree` during testing. The survey is designed to test the usage of standard oTree forms, buttons and wait pages in a session with interacting participants.

The costs of running the test on OpenAI using the "gpt-4o" model are roughly 0.10 US-$.

## More information

If you want to learn more about botex

- take a look at our botex case study, providing a code walk-through for an actual online experiment (in which you can also participate), or
- read our current and somewhat preliminary paper.

## Get in touch!

If you are interested in this project or even have already tried it, we would love to hear from you. Simply shoot an email, comment on our linkedin post, or open an issue here on GitHub!