# botex: Using LLMs as Experimental Participants in oTree

## Idea

This in-development Python package allows you to use large language models (LLMs) as bots in [oTree](https://www.otree.org) experiments. For interfacing with LLMs, it offers two options

- [litellm](https://litellm.vercel.app): Allows the use of various commercial LLMs
- [llama.cpp](https://github.com/ggerganov/llama.cpp): Allows the use of local (open source) LLMs  

While both approaches have been tested and found to work, currently, we have only used OpenAI's Chat GPT-4o model for our own research work. See further below for a list of commercial and open-source LLMs that we have verified to pass the package tests.

botex has been inspired by recent work of Grossmann, Engel and Ockenfels ([paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4682602), [repo](https://github.com/mrpg/ego)) but uses a different approach. Instead of using dedicated prompts, botex bots consecutively scrape their respective oTree participant's webpage and infer the experimental flow solely from the webpage text content. This avoids the risk of misalignment between human (webpage) and bot (LLM prompt) experimental designs and, besides facilitating the study of LLM "behavior", allows to use LLM participants to develop and pre-test oTree experiments that are designed (primarily) for human participants.

The downside of this approach is that the scraping has to rely on some level of standardization. Luckily, the oTree framework is relatively rigid, unless the user adds customized HTML forms to their experimental designs. Currently, all standard form models used by oTree are tested and verified to work. In the future, we plan to implement also customized HTML forms but likely this will require some standardization by the user implementing the experimental design.


## Usage

If you want to use botex to create LLM participants for your own oTree experiments, you need the following:

- A working python environment >= 3.10 and preferable a virtual environment.
- [Google Chrome](https://www.google.com/chrome/) for scraping the oTree participant pages.
- Access to an oTree server that you can start sessions on or at least an URL of an oTree participant link. The server can be local or remote.
- Access to an LLM model for inference. See [Verfied LLMs section](#verified-llms).

Then, install the current development version of the package that is described in this README directly from this repository: `pip install git+https://github.com/joachim-gassen/botex.git`.

If you rather want to play it safe and install the last stable PyPi version of the package, then you can install it the 'normal way' by running `pip install botex`. However, in this case, you should refer to the [readme available on Pypi](https://pypi.org/project/botex/) for pointers on how to get started.


## Using the botex command line interface

The botex package comes with a command line interface that allows you to start botex on a running oTree instance. To set one up you can do the following in your virtual environment:

```bash
pip install otree
otree startproject otree # Say yes for examples
cd otree 
otree devserver
```

Then start the botex command line interface by running `botex` in your virtual environment. You should see the following output:

```text
(.venv) user@host:~/github/project$ botex
Botex database file not provided. Defaulting to 'botex.db'
oTree server URL not provided. Defaulting to 'http://localhost:8000'
No LLM provided. Enter your litellm model string here or press enter
to accept the default ('gemini/gemini-1.5-flash'):
```

After accepting the default Gemini model you need to enter an API key. If you do not have one yet, you can get a free one from the [Google AI Studio](https://ai.google.dev). After entering the key, you can select an oTree experiment from the examples offered by the fresh oTree installation:

```text
Enter the API key for your LLM model (for the Gemini model,
you can get a free API key at https://aistudio.google.com/apikey):***
Available session configurations:
1: guess_two_thirds
2: survey
Select a configuration by number: 
```

We suggest that you choose the Guess two Thirds game.

```text
Selected session configuration: guess_two_thirds
Number of participants: 3
Number of human participants: 0
Session 'ouwx1xnb' initialized
You can monitor its progress at http://localhost:8000/SessionMonitor/ouwx1xnb
Starting bots on session...
```

You can monitor how the three bots complete the experiment. After they are done, you can store the botex data from the run.

```text
Session complete. You can view the oTree data at http://localhost:8000/SessionData/ouwx1xnb
Download the oTree data at: http://localhost:8000/export
Enter CSV file name to export botex data to or press Enter to skip: 
```

The resulting CSV file will contain data similar to the following table

| session_id   | participant_id   |   round | question_id   |   answer | reason                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|--------------|------------------|---------|---------------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ouwx1xnb     | j14kfulq         |       1 | id_guess      |       67 | I will start by choosing a number above 0.  In this game, the goal is to get as close as possible to two-thirds of the average of all numbers submitted by players.  Since it is the first round and I do not know what other people will do, I choose a number which is roughly in the middle.                                                                                                                                                                                 |
| ouwx1xnb     | j14kfulq         |       2 | id_guess      |        0 | In the first round, two-thirds of the average was 36.89, and the closest guess was 33.  In the second round, if everyone plays the same strategy again, the average of 33, 33, and 33 would be 33, and two-thirds of the average would still be 33.  To win, I should pick 0 to try and get close to that two-thirds value.  If the other players also realize this, then the average will be lower and the two-thirds average will be even lower, and 0 will be a safe choice. |
| ouwx1xnb     | j14kfulq         |       3 | id_guess      |        0 | Following the iterative reasoning from the previous rounds, if all players continue to use the same logic, the average should approach zero. Therefore, choosing 0 is the most strategically sound choice.                                                                                                                                                                                                                                                                      |
| ouwx1xnb     | 8o1f9cf9         |       1 | id_guess      |       66 | I will start with a number close to 2/3 of 100                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ouwx1xnb     | 8o1f9cf9         |       2 | id_guess      |       33 | In the first round, the average was 52, two thirds of the average is 34.67, and the closest guess was 33. I will guess 33 again, hoping others also guess 33.                                                                                                                                                                                                                                                                                                                   |
| ouwx1xnb     | 8o1f9cf9         |       3 | id_guess      |        0 | Given the pattern of previous rounds, it's likely that players will try to anticipate each other's moves, potentially leading to a convergence toward lower numbers.  I will choose 0, hoping to be closest to two-thirds of the average.                                                                                                                                                                                                                                       |
| ouwx1xnb     | 1xctv42x         |       1 | id_guess      |       33 | I will start by guessing 33.  This is a common starting point in this type of game, based on iterative reasoning and assuming other players will also use a similar strategy.                                                                                                                                                                                                                                                                                                   |
| ouwx1xnb     | 1xctv42x         |       2 | id_guess      |       30 | In the first round, two-thirds of the average was close to 37. I believe that many players will expect this, and thus will choose a number around this value. I will go slightly lower, to account for the fact that many others will choose around 37.                                                                                                                                                                                                                         |
| ouwx1xnb     | 1xctv42x         |       3 | id_guess      |       10 | Given the previous rounds' two-thirds averages of 36.89 and 14.0, there is a clear downward trend.  I anticipate other players will also recognize this pattern and adjust their guesses accordingly.  To avoid being too close to the average, I will choose a relatively low number hoping to beat any average that will be close to 0.                                                                                                                                       |

If you are interested in the additional options that the command line interface offers, we suggest you take a peek by running `botex -h`.

## Running botex in your own code

After installing botex, you should be able to start botex on an existing oTree participant link by running the following code snippet

```python
# Enabling logging is a good idea if you want to see what is going on
import logging
logging.basicConfig(level=logging.INFO)

import botex

# Running a botex bot on a specific oTree participant link
botex.run_single_bot(
    botex_db = "path to a sqlite3 file that will store the bot data (does not have to exist)", 
    session_name = "session config name of your oTree experiment (defaults to 'unknown')", 
    session_id = "session ID of your oTree experiment (defaults to 'unknown')", 
    url = "the URL of the participant link", 
    model = "The LLM model that you want to use (defaults to 'gpt-4o-2024-08-06')",
    api_key = "The API key for your model (e.g., OpenAI)"
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
    botex_db = "path to a sqlite3 file (does not have to exist)",
    otree_server_url = "url of your server, e.g., http://localhost:8000]",
    otree_rest_key = "your oTree API key, if set and needed"
)

# The returned dict will contain the oTree session ID, all participant codes, 
# human indicators, and the URLs separately for the LLM and human participants.
# You can now start all LLM participants of the session in one go.  
botex.run_bots_on_session(
    session_id = sdict['session_id'],  
    botex_db = "same path that you used for initializing the session", 
    model = "The LLM model that you want to use (defaults to 'gpt-4o-2024-08-06')",
    api_key = "The API key for your model (e.g., OpenAI)"
)
```

After the bots have completed their runs, you should have their response data stored in your oTree database just as it is the case for human participants. If you are interested in exploring the botex data itself, which is stored in the sqlite3 file that you provided, we recommend that you take a look at our botex [walk-through](https://github.com/trr266/botex_examples).

## Verified LLMs

The model that you use for inference has to support [structured outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/). We have tested botex with the following LLMs:

| Vendor | Model | Link | Status | Notes |
| --- | --- | --- | --- | --- |
| OpenAI | gpt-4o-2024-08-06 and later | [OpenAI API](https://openai.com/api/) | OK | Requires at least paid user tier 1 |
| OpenAI |  gpt-4o-mini-2024-07-18 and later | [OpenAI API](https://openai.com/api/) | OK | Requires at least paid user tier 1  |
| Google | gemini/gemini-1.5-flash-8b | [Google AI Studio](https://ai.google.dev) | OK | 1,500 requests per day are free |
| Google | gemini/gemini-1.5-flash | [Google AI Studio](https://ai.google.dev) | OK | 1,500 requests per day are free |
| Google | gemini/gemini-1.5-pro | [Google AI Studio](https://ai.google.dev) | OK | 50 requests per day are free (not usable for larger experiments in the free tier) |
| Open Source | Mistral-7B-Instruct-v0.3.Q4_K_M.gguf | [Hugging Face](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3) | OK | Run as a local model (see below) |
| Open Source | qwen2.5-7b-instruct-q4_k_m.gguf | [Hugging Face](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF)  | OK | Run as a local model (see below) |


If you have success running botex with other models, please let us know so that we can add them to the list.

The default model that botex uses is `gpt-4o-2024-08-06`. If you want to use a different model, you can specify it in the `run_single_bot()` or `run_bots_on_session()` call by providing the model string from the table above as `model` parameter. In any case, you have to provide the API key for the model that you want to use.


## Use of local LLMs

If you want to use a local LLM instead of commercial APIs via the litellm interface you need, in addition to the above:

1. **Set up `llama.cpp`**:
   - Clone the `llama.cpp` repository from [this link](https://github.com/ggerganov/llama.cpp).
   - Make sure to use commit [`cda0e4b`](https://github.com/ggerganov/llama.cpp/commit/cda0e4b648dde8fac162b3430b14a99597d3d74f), the latest release as of this writing (Oct 20, 2024), to ensure compatibility and smooth performance.
   - Follow the instructions provided in the repository to build `llama.cpp`.

2. **Download a Local LLM Model**:
   - For optimal performance and compatibility, we recommend using the current leading model [Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF) from Hugging Face, which is available in the GGUF format.
   - You should refer to the model's documentation for specific instructions on which quantized model to download and how much memory it requires.

Then all that you need to do is to adjust the botex calls from above by specifying the model and its configuration. You do this by providing a dict that will become a `LocalLLM` object to the botex calls that start bots. For example, for `botex.run_bots_on_session()`, your call would look something like this

```python
botex.run_bots_on_session(
    session_id = sdict['session_id'],  
    botex_db = "same path that you used for initializing the session", 
    model = "local",
    local_model_cfg = {
        "path_to_llama_server": "the path to the llama.cpp llama-server",
        "local_llm_path": "the path to your LLM model GGUF file"
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

- take a look at our [botex examples repo](https://github.com/trr266/botex_examples), providing a code walk-through for an actual online experiment (in which you can also participate), or
- read our current and somewhat preliminary [paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4891763).

## Get in touch

If you are interested in this project or even have already tried it, we would love to hear from you. Simply shoot an email, comment on our linkedin post, or open an issue here on GitHub!