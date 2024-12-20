# botex: Using LLMs as Experimental Participants in oTree 

This in-development Python package allows you to use large language models (LLMs) as bots in [oTree](https://www.otree.org) experiments. It has been inspired by recent work of Grossmann, Engel and Ockenfels ([paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4682602), [repo](https://github.com/mrpg/ego)) but uses a different approach. Instead of using dedicated prompts, botex bots consecutively scrape their respective oTree participant's webpage and infer the experimental flow solely from the webpage text content. This avoids the risk of misalignment between human (webpage) and bot (LLM prompt) experimental designs and, besides facilitating the study of LLM "behavior", allows to use LLM participants to develop and pre-test oTree experiments that are designed (primarily) for human participants.

The downside of this approach is that the scraping has to rely on some level of standardization. Luckily, the oTree framework is relatively rigid, unless the user adds customized HTML forms to their experimental designs. Currently, all standard form models used by oTree are tested and verified to work. In the future, we plan to implement also customized HTML forms but likely this will require some standardization by the user implementing the experimental design.

For interfacing with LLMs, botex offers two options

- [litellm](https://litellm.vercel.app): Allows the use of various commercial LLMs
- [llama.cpp](https://github.com/ggerganov/llama.cpp): Allows the use of local (open source) LLMs  

While both approaches have been tested and found to work, currently, we have only used OpenAI's Chat GPT-4o model for our own research work. See further below for a list of commercial and open-source LLMs that we have verified to pass the package tests.
