# botex: Using LLMs as Experimental Participants in oTree

## Idea

This in-development Python package allows you to use large language models (LLMs) as bots in [oTree](https://www.otree.org) experiments. As it relies on the [litellm](https://litellm.vercel.app) infrastructure, in principle, various commercial and open source LLM models could be used as bots. Currently, however, only OpenAI's Chat GPT-4 model has been tried and tested to perform well.

While botex has been inspired by [recent work](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4682602), it uses a different approach. Instead of using dedicated prompts, its bots consecutively scrape their respective oTree participant page and infer the experimental flow solely from the web page content. This avoids the risk of misalignment between human (web page) and bot (LLM prompt) experimental designs and, besides facilitating the study of LLM "behavior", allows to use bots to develop and pre-test oTree experiments that are designed (primarily) for human participants.

The downside of this approach is that the scraping has to rely on some level of standardization. Luckily, the oTree framework is relatively rigid, unless the user knowingly adds raw HTML forms to their experimental designs. Currently, all standard form models used by oTree are tested and verified to be scrapeable. In the future, we plan to implement also customized HTML forms but likely this will require some standardization by the user implementing the experimental design.

## Installation

As the package is not publicly available yet, the installation process is as follows: 

1. Copy `_secret.env` to `secret.env` and edit. Most importantly, you have to set your OpenAI key. As the otree instance will only be used for testing, you can set any password and rest key that you like.
2. Set up a virtural environment `python3 -m venv .venv`
3. Activate it `source .venv/bin/activate`
4. Install the necessary packages `pip install -r requirements.txt`
5. Install the BotEx package locally and editable `pip install -e .`
6. Test whether everything works `.venv/bin/pytest`

If it works you should see a test output similar to this one:

```
=========================== test session starts ===========================
platform darwin -- Python 3.12.2, pytest-8.1.1, pluggy-1.4.0
rootdir: /Users/joachim/github/BotEx
configfile: pyproject.toml
plugins: anyio-4.3.0, dependency-0.6.0
collected 11 items                                                        

tests/test_a_botex_db.py .                                          [  9%]
tests/test_b_otree.py .....                                         [ 54%]
tests/test_c_bots.py .....                                          [100%]

------------------------------ Bots answers -------------------------------
Question: What is your favorite color?'
Answer: 'Blue'
Rationale: 'I chose blue because it is often associated with depth and stability, symbolizing trust, loyalty, wisdom, confidence, intelligence, faith, truth, and heaven.'.

Question: What is your favorite number?'
Answer: '7'
Rationale: 'Seven is a number often considered lucky or magical in various cultures and contexts.'.

Question: Do you like ice cream?'
Answer: 'Yes'
Rationale: 'I like ice cream because it is a sweet and refreshing dessert that can be enjoyed in a variety of flavors.'.

Question: Which statement do you most agree with?'
Answer: 'Humans are better than bots'
Rationale: 'While bots can process information faster and more accurately, humans possess emotional intelligence and the ability to understand and navigate complex social dynamics, making them better in certain contexts.'.

Question: What do you enjoy doing most?'
Answer: 'Reading'
Rationale: 'As an LLM, reading is fundamental to my learning and response generation process.'.

Question: How many people live on the earth currently (in billions)?'
Answer: '7.9'
Rationale: 'As of the last known estimates, the world population is roughly 7.9 billion.'.

Question: Do you have any feedback that you want to share?'
Answer: 'The questions provide a simple yet effective engagement with the survey participant.'
Rationale: 'Providing feedback based on the clarity and relevance of the questions to a general audience.'.

====================== 11 passed in 85.46s (0:01:25) ======================
```

You see that it also contains some questions and answers. They are also accessible in `test/questions_and_answers.csv` after the run and were given by two bot instances in the oTree test survey `test/otree` during testing. The survey is designed to test the usage of standard oTree forms, buttons and wait pages in a session with interacting participants.

The costs of running the test on OpenAI using the "gpt-4-turbo-preview" model are roughly 0.10 US-$.

## Workflow

Assuming that pytest succeeded, you should be able to run LLM bots by

1. setting up a plain vanilla oTree app (no raw HTML forms),
2. starting your oTree server, and
3. running something like

```{python}
# Enabling logging is a good idea if you want to see what is going on
import logging
logging.basicConfig(level=logging.INFO)

import botex

sdict = botex.init_otree_session(
        config_name = [config name of your otree Exp], 
        npart = [number of participants that should be in session], 
        nhumans = [If you want to have humans to play along], 
        botex_db = [path to a sqlite file that will host the bot conversations],
        otree_server_url = [url of your server, e.g., http://localhost:8000],
        otree_rest_key = [the secret key of your oTree API]
    )

botex.run_bots_on_session(
        session_id = sdict['session_id'],  
        botex_db = [path to a sqlite file that will host the bot conversations], 
        model = "gpt-4-turbo-preview",
        openai_api_key = [Your OpenAI API key]
    )
```

After that, your oTree instance should have data for you and extensive information on the bot conversation will be available in the botex sqlite3 file that you provided. Have fun exploring.

## To Do

- [X] Check whether one can lump together the summary and the analyse prompt (maybe even the question prompt?) This would save quite some tokens and speed up things
- [X] Rewrite to use [LiteLLM](https://github.com/BerriAI/litellm). This should make it relatively easy to replace Chat GPT for alternative and even local LLMs.
- [X] Convert the one shot trust game to multiple rounds (but still allowing only one round)
- [X] Improve the general usability of the bot by applying it to a more complex experiment with different form fields (maybe osacc?)
- [X] Develop a prompting variant that asks the LLM to summarize the game so far, so that the message history of multiple round games does not get excessively long. 
- [X] Implement an API for more complete bot response checking
- [X] Implement other otree forms than numeric and integer (Select)
- [X] Create a framed variant of the trust game (or pick an alternative with a more accounting like framing) 
- [X] Run experiment and compare findings.
- [ ] Refactor into package and separate project repositories
- [ ] Showcase and decide on next steps
