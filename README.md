# LLM models as Experimental Agents: The Role of Accounting Framing

## Idea

In this project I intend to study how LLMs perform in classic accounting experiments, relative to their economic or psychological blueprints.

Accounting experiments typically use an accounting framing, often without hypothesizing or testing the framing effect per se. As an example, the recent budget experiment games in accounting are conceptually relatively close to cheap talk games in economics.

Building on [recent work](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4682602) I develop a framework that allows LLM agents to participate in [oTree](https://www.otree.org) experiments by consecutively scraping their participant web page.

As a starting point, using this setup, I intend to compare the behavior of LLMs in a classic neutral investment trust game, to their behavior in a game where the trustor is framed to be an investor and the trustee is characterized as a manager.

## Setup

1. Copy `_secret.env` to `secret.env` and edit.
2. Set up a virtural environment `python3 -m venv venv`
3. Activate it `source venv/bin/activate`
4. Install the necessary packages `pip install -r requirements.txt`
5. Start a local otree server `cd otree && otree devserver`
6. Run `python code/run_otree_session.py`

## To Do

- [X] Check whether one can lump together the summary and the analyse prompt (maybe even the question prompt?) This would save quiet some tokens and speed up things
- [ ] Rewrite to use [LiteLLM](https://github.com/BerriAI/litellm). This should make it relatively easy to replace Chat GPT for alternative and even local LLMs.
- [ ] Implement the framed variant of the one shot trust game.
- [ ] Run experiment and compare findings.
