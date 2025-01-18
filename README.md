# botex: Using LLMs as Experimental Participants in oTree 

## Overview

Welcome to the GitHub repository botex, a new Python package that leverages the power of **large language models (LLMs) as participants in oTree experiments**.

botex takes a novel approach to integrating LLMs into behavioral experiments. Rather than relying on predefined prompts,[^1] **botex bots dynamically interact with their experimental environment by scraping their respective oTree participant pages**. This approach allows them to infer the experimental flow solely from the webpage's textual content. By aligning bot behavior directly with the experimental interface, botex eliminates potential discrepancies between human and bot designs. This not only opens up **exciting opportunities to explore LLM behavior** but also positions LLMs as a **powerful tool for developing and pre-testing experiments** intended for human participants.

[^1]:  See, for example, Grossmann, Engel and Ockenfels ([paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4682602), [repo](https://github.com/mrpg/ego))

<p style="text-align: center;">
  <img src="https://raw.githubusercontent.com/joachim-gassen/botex/main/docs/assets/images/index_botex_workflow.svg" alt="botex Workflow" width="80%">
</p>

## Why Choose botex?

botex's innovative approach offers several advantages:

- **Alignment**: By scraping oTree pages, LLMs respond to the same interface as human participants, ensuring consistency in experimental design.
- **Pre-testing**: LLMs can act as intelligent pre-testers, providing valuable feedback during the design phase of human-centric experiments.
- **Behavioral Insights**: Explore how LLMs interact and respond under experimental conditions designed for humans.

## Requirements

- A working python environment >= 3.10 and preferably a virtual environment.
- [Google Chrome](https://www.google.com/chrome/) for scraping the oTree participant pages.

## Documentation

For learning how to use botex in your project, please refer to the [package documentation](https://botex.trr266.de).

## Problems and Bugs

If you encounter any problems or bugs, please open a [GitHub issue]((https://github.com/joachim-gassen/botex/issues)) on this repository.

## Paper

If you use botex in your research, please cite its accompanying paper:

> Fikir Worku Edossa, Joachim Gassen, and Victor S. Maas (2024): Using Large Language Models to Explore Contextualization Effects in Economics-Based Accounting Experiments. Working Paper. [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4891763).


## Get in touch

If you are interested in this project or even have already tried it, we would love to hear from you. Simply shoot an email, reach out on BlueSky or LinkedIn, or open an issue here on GitHub!


## Development

The reminder of this readme is dedicated to the development of botex. If you want to contribute to the project, please keep reading.

### Installation for Development

1. Clone this repository: `git clone https://github.com/joachim-gassen/botex` 
2. Copy `_botex.env` to `botex.env` and edit. Most importantly, you have to set your API key(s) and the configuration of the local llama.cpp instance that you want botex to start. See point 8 below if you only want to start pytest on a specific LLM setup. As the otree instance will only be used for testing, you can set any password and rest key that you like.
3. Set up a virtural environment `python3 -m venv .venv`
4. Activate it `source .venv/bin/activate`
5. Install the necessary packages `pip install -r requirements.txt`
6. Install the botex package locally and editable `pip install -e .`
7. Run the tests with `pytest`. By default it runs tests using the default OpenAI model and the llama.cpp model. For both models, you need to make sure that you provide the necessary configuration in `botex.env`
8. If you want to test specific LLM setups, you can pass the model name as an argument to pytest, e.g., `pytest --model gemini/gemini-1.5-flash`. You can provide multiple models if you like, e.g., `pytest --model gemini/gemini-1.5-flash llamacpp`. If you want to test a specific local model via llama.cpp make sure to set the model path in `botex.env`.

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