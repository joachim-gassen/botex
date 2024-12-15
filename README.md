# botex: Using LLMs as Experimental Participants in oTree

## Idea

This in-development Python package allows you to use large language models (LLMs) as bots in [oTree](https://www.otree.org) experiments. It has been inspired by recent work of Grossmann, Engel and Ockenfels ([paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4682602), [repo](https://github.com/mrpg/ego)) but uses a different approach. Instead of using dedicated prompts, botex bots consecutively scrape their respective oTree participant's webpage and infer the experimental flow solely from the webpage text content. This avoids the risk of misalignment between human (webpage) and bot (LLM prompt) experimental designs and, besides facilitating the study of LLM "behavior", allows to use LLM participants to develop and pre-test oTree experiments that are designed (primarily) for human participants.

The downside of this approach is that the scraping has to rely on some level of standardization. Luckily, the oTree framework is relatively rigid, unless the user adds customized HTML forms to their experimental designs. Currently, all standard form models used by oTree are tested and verified to work. In the future, we plan to implement also customized HTML forms but likely this will require some standardization by the user implementing the experimental design.

For interfacing with LLMs, botex offers two options

- [litellm](https://litellm.vercel.app): Allows the use of various commercial LLMs
- [llama.cpp](https://github.com/ggerganov/llama.cpp): Allows the use of local (open source) LLMs  

While both approaches have been tested and found to work, currently, we have only used OpenAI's Chat GPT-4o model for our own research work. See further below for a list of commercial and open-source LLMs that we have verified to pass the package tests.


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


## Using Local Models with llama.cpp

If you want to use a local LLM instead of commercial APIs via the litellm interface, llama.cpp is the most reliable and performant option. You will need to install llama.cpp on your system and start the llama-server with a local LLM model.

### Installation

- **MacOS/Linux**: Install `llama.cpp` via Homebrew for a straightforward setup:
  ```bash
  brew install llama.cpp
  ```
- **Windows**:
  - The recommended approach is to download precompiled binaries from the [llama.cpp releases page](https://github.com/ggerganov/llama.cpp/releases).
  - Alternatively, you can clone the repository and build it manually following the provided instructions.

#### Precompiled Binaries

Download the appropriate binary for your system from the [llama.cpp releases page](https://github.com/ggerganov/llama.cpp/releases). Refer to the release page to identify the binary suitable for your hardware and system.

### Running llama-server

After downloading and extracting the llama.cpp binary, you can start the llama-server with the desired LLM model from huggingface with the following command:

```bash
llama-server --model-url https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf\?download\=true -c context length you want to use -n maximum number of tokens you want to generate at a time

# Additional options:
# -ngl number of layers to offload to gpu (if you have a GPU with a good amount of memory you should try to offload as many layers as possible)
# -fa if you want to enable flash attention (recommended for performance)
```

### Running botex with a Local LLM

Then all that you need to do is to adjust the botex calls from above by choosing `llamacpp` as a model.

```python
botex.run_bots_on_session(
    session_id = sdict['session_id'],  
    botex_db = "same path that you used for initializing the session", 
    model = "llamacpp",
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
7. Run the tests with `pytest`. By default it runs tests using the default OpenAI model and the llama.cpp model. For both models, you need to make sure that you provide the necessary configuration in `secrets.env`
8. If you want to test other models, you can pass the model name as an argument to pytest, e.g., `pytest --model gemini/gemini-1.5-flash`. You can provide multiple models if you like, e.g., `pytest --model gemini/gemini-1.5-flash llamacpp`.

If it works you should see a test output similar to this one:

```
(.venv) joachim@JoachimsMBP729 botex % pytest
=========================== test session starts ================================
platform darwin -- Python 3.12.7, pytest-8.1.1, pluggy-1.4.0
rootdir: /Users/joachim/github/botex
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.3.0, cov-4.1.0, dependency-0.6.0
collected 49 items                                                                                 

tests/test_a_botex_db.py .                                               [  4%]
tests/test_b_otree.py ......                                             [ 28%]
tests/test_c_bots.py ................                                    [ 92%]
tests/test_d_exports.py ..                                               [100%]

------------------------- Answers from 'gpt-4o-2024-08-06' ---------------------
Question: 'Select a button'
Answer: 'Blue Pill'
Rationale: 'I am not given any additional context or information that 
differentiates between the options. Therefore, I will select the 'Blue Pill'
randomly.'

Question: 'What is your favorite color?'
Answer: 'Blue'
Rationale: 'I like the tranquility and calmness it represents'

Question: 'What is your favorite number?'
Answer: '7'
Rationale: 'I always found it to be a powerful and balanced number'

Question: 'Do you like ice cream?'
Answer: 'Yes'
Rationale: 'I enjoy the taste of ice cream and different flavors'

Question: 'Which statement do you most agree with?'
Answer: 'Humans are better than bots'
Rationale: 'I believe humans have creativity and the capacity for emotional 
understanding, which are important traits'

Question: 'Select a button'
Answer: 'Blue Pill'
Rationale: 'The page asks me to choose between two options: Blue Pill and Red 
Pill, as part of a decision-making exercise. I will choose the Blue Pill as it 
is often associated with staying in a familiar, stable reality.'

Question: 'What do you enjoy doing most?'
Answer: 'Reading'
Rationale: 'The options provided cater to various activities. Based on random 
selection, I'll choose 'Reading' as it is a common enjoyable activity for many 
individuals.'

Question: 'How many people live on the earth currently (in billions)?'
Answer: '8.0'
Rationale: 'Current estimates of the global population are around 8 billion. 
Therefore, I will answer with this figure.'

Question: 'Do you have any feedback that you want to share?'
Answer: 'No feedback at the moment.'
Rationale: 'There is no specific feedback to provide as the process went
 smoothly.'

-------------------------- Answers from 'llamacpp' -----------------------------
Question: 'Select a button'
Answer: 'Blue Pill'
Rationale: 'I have chosen the pill that appears more interesting or relevant 
to me, in this case, I chose the Blue Pill.'

Question: 'What is your favorite color?'
Answer: 'blue'
Rationale: 'My favorite color is blue, as it is calming and serene.'

Question: 'What is your favorite number?'
Answer: '7'
Rationale: 'My favorite number is 7, as it is the number of days in a week.'

Question: 'Do you like ice cream?'
Answer: 'Yes'
Rationale: 'I do enjoy ice cream, as it is a delicious and refreshing treat.'

Question: 'Which statement do you most agree with?'
Answer: 'Bots are better than humans'
Rationale: 'While both statements have their merits, I lean towards the 
perspective that bots and humans each have their own unique strengths and can 
complement each other, rather than one being inherently better than the other.'

Question: 'Select a button'
Answer: 'Blue Pill'
Rationale: 'I have chosen the Blue Pill, as it represents the choice to continue
with the known and predictable, which aligns with the purpose of this survey.'

Question: 'What do you enjoy doing most?'
Answer: 'Reading'
Rationale: 'I enjoy reading the most as it allows me to gain new knowledge and 
perspectives.'

Question: 'How many people live on the earth currently (in billions)?'
Answer: '7.9'
Rationale: 'I estimate the current population of the earth to be around 
7.9 billion people.'

Question: 'Do you have any feedback that you want to share?'
Answer: 'Thank you for the opportunity to participate in this survey. I 
appreciate the developers' work and hope the results will be beneficial.'
Rationale: 'I appreciate the opportunity to participate in this survey and test 
the functionality of the python package. I hope the results will be useful for 
the developers.'

====================== 25 passed in 208.60s (0:03:28) ==========================
```

If something goes wrong, you can repeat the test with logging (`pytest -o log_cli=true`) to see what is going wrong.

You see that it also contains some questions and answers. They are also accessible in `test/questions_and_answers.csv` after the run and were given by two bot instances in the oTree test survey `test/otree` during testing. The survey is designed to test the usage of standard oTree forms, buttons and wait pages in a session with interacting participants.

The costs of running the test on OpenAI using the "gpt-4o" model are roughly 0.10 US-$.

## More information

If you want to learn more about botex

- take a look at our [botex examples repo](https://github.com/trr266/botex_examples), providing a code walk-through for an actual online experiment (in which you can also participate), or
- read our current [paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4891763) using botex to explore the contexutalization effects in accounting experiments.

## Get in touch

If you are interested in this project or even have already tried it, we would love to hear from you. Simply shoot an email, comment on our linkedin post, or open an issue here on GitHub!