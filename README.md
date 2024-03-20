# BotEx: Using LLMs as Experimental Participants in oTree

## Idea

The purpose of this project is two-fold:

1. I introduce the framework BotEx that allows to use large language models (LLM) as bots for oTree experiments. Different from [prior work](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4682602), my framework does not require the development of dedicated prompts. Instead, its bots consecutively scrape their respective oTree participant page and infer the
experimental flow solely from the web page content. This avoids the risk of misalignment between human (web page) and bot (LLM prompt) experimental designs and, besides facilitating the study of LLM "behavior", allows to use bots to develop and pre-test oTree experiments that are designed (primarily) for human participants. 
2. I use this framework to study the effect of context framing on experimental findings in classic economic experiments. Accounting experiments typically use an accounting framing, often without hypothesizing or testing the framing effect per se. Using BotEx to test for the effect of a certain contextual framing can inform the researcher about how likely it is to affect the findings in a setting with human participants.

As a starting point, using this setup, I compare the response behavior of LLMs in a classic [neutral investment trust game](https://doi.org/10.1006/game.1995.1027), to their behavior in a game where the trustor is framed to be an investor and the trustee is characterized as a manager. Based on a small sample of LLM runs (30 for each experiment), I find that, in the framed experiment, sending LLMs send significantly larger amounts to receiving LLMs while the share that the receiving LLMs return are not significantly different from the neutral experiment.

## Setup

1. Copy `_secret.env` to `secret.env` and edit.
2. Set up a virtural environment `python3 -m venv venv`
3. Activate it `source venv/bin/activate`
4. Install the necessary packages `pip install -r requirements.txt`
5. Start a local otree server `cd otree && export OTREE_PRODUCTION=1 && otree devserver`
6. Run `python code/run_otree_session.py`

## To Do

- [X] Check whether one can lump together the summary and the analyse prompt (maybe even the question prompt?) This would save quite some tokens and speed up things
- [X] Rewrite to use [LiteLLM](https://github.com/BerriAI/litellm). This should make it relatively easy to replace Chat GPT for alternative and even local LLMs.
- [X] Convert the one shot trust game to multiple rounds (but still allowing only one round)
- [X] Improve the general usability of the bot by applying it to a more complex experiment with different form fields (maybe osacc?)
- [X] Develop a prompting variant that asks the LLM to summarize the game so far, so that the message history of multiple round games does not get excessively long. 
- [X] Implement an API for more complete bot response checking
- [ ] Implement other otree forms than numeric and integer (Select)
- [X] Create a framed variant of the trust game (or pick an alternative with a more accounting like framing) 
- [X] Run experiment and compare findings.
- [ ] Showcase and decide on next steps
