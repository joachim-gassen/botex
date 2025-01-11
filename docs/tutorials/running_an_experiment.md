# Run an oTree Experiment with botex

## Starting oTree via Python

When you want to run an oTree experiment with botex bots, you need to have access to a running oTree instance that is able to host th experiment that you want to run. 

in the [getting started section](../getting_started.md), we have seen how to start an oTree server via the command line. Here, we will use botex to start an oTree server instance via Python. This is useful if you want to automate the process of running the experiment and collecting the data.

The following code snippet shows how to start an oTree server via Python:

```python
import botex

# botex is silent by default. If you want to understand
# what it is doing, it is useful to enable logging 
import logging
logging.basicConfig(level=logging.INFO)

# Start the oTree server
botex.start_otree_server(project_path="otree")
```

Adjust the `project_path` parameter to where you installed your otree project. The above starts a development oTree server without authentication. If you want to require authentication (recommended for publicly accessible servers), you can set the `auth_level` parameter of `start_otree_server` to `'STUDY'`. In this case, you should also set the parameters `rest_key` and `admin_password`.

Running the snippet from above, you should see the following output:

```text
INFO:botex:oTree server started successfully with endpoint 'http://localhost:8000'
```

Please note that the oTree sever instance will terminate when your script terminates. 


## Retrieve the available session configurations

Before you can run an experiment, you might want to know which session configurations are available. The extension of the code shows how to retrieve the available session configurations from a running oTree server:

```python
import botex

import logging
logging.basicConfig(level=logging.INFO)

# Start the oTree server
otree_process = botex.start_otree_server(project_path="otree")

# Retrieve the session configurations
session_configs = botex.get_session_configs(
    otree_server_url="http://localhost:8000"
)
print(session_configs)

# Stop the oTree server
botex.stop_otree_server(otree_process)

```

If you are using a locally running oTree server, you can omit the `otree_server_url` parameter. When you are accessing a remotely running oTree server, you need to provide its URL (including the correct port if required). If you try to access an oTree server with authentication, you also need to provide the `rest_key` parameter. Besides querying the session config from the server, we also added a call to `stop_otree_server` to gracefully terminate the oTree server instance before ending the script.

The output of the above script should look like this:

```text 
INFO:botex:oTree server started successfully with endpoint 'http://localhost:8000'
[{'real_world_currency_per_point': 1.0, 'participation_fee': 0.0, 'doc': '', 
'name': 'guess_two_thirds', 'display_name': 'Guess 2/3 of the Average', 
'app_sequence': ['guess_two_thirds', 'payment_info'], 
'num_demo_participants': 3}, 
{'real_world_currency_per_point': 1.0, 'participation_fee': 0.0, 'doc': '', 
'name': 'survey', 'app_sequence': ['survey', 'payment_info'], 
'num_demo_participants': 1, 'display_name': 'survey'}]
INFO:botex:oTree server stopped.
```

## Initialize a session

Once you know which session configurations are available, you can initialize a session. The extension of the code shows how to do this:

```python
import botex

import logging
logging.basicConfig(level=logging.INFO)

# Start the oTree server
otree_process = botex.start_otree_server(project_path="otree")

# Retrieve the session configurations
session_configs = botex.get_session_configs(
    otree_server_url="http://localhost:8000"
)

# Initialize a session
session = botex.init_otree_session(
    config_name=session_configs[0]['name'], # "guess_two_thirds"
    npart = 3,
    otree_server_url="http://localhost:8000",
    botex_db = 'botex.sqlite'
)

print(session)

# Stop the oTree server
botex.stop_otree_server(otree_process)
```

Again, adjust the `otree_server_url` parameter and add `rest_key` as required. `init_otree_session()` requires the session config name and the number of participants to include. When changing this parameter, make sure that the experiment supports it. E.g., the Guess two Thirds game provided as an example with the oTree installation requires participants to be multiples of three. In addition, we need to provide a file for the SQLite database where botex stores its data. If the file does not exist, it will be created. If it exists, the data will be appended.

`init_otree_session()` returns a dict with session data, including the session ID and the participant URLs. The output of the above script should look like this:

```text
INFO:botex:oTree server started successfully with endpoint 'http://localhost:8000'
{'session_id': 'lry96cc8', 
'participant_code': ['dlg5vdbq', 'j8y24ubc', 'pbewmoh2'], 
'is_human': [False, False, False], 
'bot_urls': ['http://localhost:8000/InitializeParticipant/dlg5vdbq', 
'http://localhost:8000/InitializeParticipant/j8y24ubc', 
'http://localhost:8000/InitializeParticipant/pbewmoh2'], 
'human_urls': []}
INFO:botex:oTree server stopped.
```

You see that we initialized a session with three participants, all of which are bots. The bot URLs are provided in the `bot_urls` list.

## Running botex bots on a session

Once you have initialized a session, you can run the botex bots on it. Let's extend our code:

```python
import botex

import logging
logging.basicConfig(level=logging.INFO)

# Start the oTree server
otree_process = botex.start_otree_server(project_path="otree")

# Retrieve the session configurations
session_configs = botex.get_session_configs(
    otree_server_url="http://localhost:8000"
)

# Initialize a session
session = botex.init_otree_session(
    config_name=session_configs[0]['name'], # "guess_two_thirds"
    npart = 3,
    otree_server_url="http://localhost:8000",
    botex_db = 'botex.sqlite'
)

# Run the bots on the session
botex.run_bots_on_session(
    session_id=session['session_id'],
    otree_server_url="http://localhost:8000",
    botex_db = 'botex.sqlite',
    model="gemini/gemini-1.5-flash",
    api_key="***"
)

# Stop the oTree server
botex.stop_otree_server(otree_process)
```

If it works, you will be greeted with a very long log ouput, detailing the botex bots' interactions with the oTree server. If you want to see less of this, you can adjust the logging level to `logging.WARNING` or disable logging. However, we suggest that you take a good look at the log output to familiarize yourself with the workflow of the botex bots.

The output should start and end like this:

```text
INFO:botex:oTree server started successfully with endpoint 'http://localhost:8000'
INFO:botex:Running bots on session q4ntmcdt. You can monitor the session at http://localhost:8000/SessionMonitor/q4ntmcdt
INFO:botex:Running bot with parameters: {"botex_db": "botex.sqlite", "session_id": "q4ntmcdt", "full_conv_history": false, "model": "gemini/gemini-1.5-flash", "api_key": "******", "api_base": null, "user_prompts": null, "throttle": false, "otree_server_url": "http://localhost:8000", "url": "http://localhost:8000/InitializeParticipant/372wu8py"}
INFO:botex:Running bot with parameters: {"botex_db": "botex.sqlite", "session_id": "q4ntmcdt", "full_conv_history": false, "model": "gemini/gemini-1.5-flash", "api_key": "******", "api_base": null, "user_prompts": null, "throttle": false, "otree_server_url": "http://localhost:8000", "url": "http://localhost:8000/InitializeParticipant/ay4nos1w"}
INFO:botex:Running bot with parameters: {"botex_db": "botex.sqlite", "session_id": "q4ntmcdt", "full_conv_history": false, "model": "gemini/gemini-1.5-flash", "api_key": "******", "api_base": null, "user_prompts": null, "throttle": false, "otree_server_url": "http://localhost:8000", "url": "http://localhost:8000/InitializeParticipant/nr4th0it"}
INFO:httpx:HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=****** "HTTP/1.1 200 OK"
INFO:botex:Bot's response to start message:
{
    "task": "I am participating in an online survey or experiment.  My task is to provide JSON formatted responses based on prompts that will include a summary of the survey/experiment so far and any new information to be added to the summary. This summary will function as my memory throughout the experiment.  Each prompt also includes scraped text from a webpage related to the survey/experiment.  I will analyze the text, answer any questions or complete tasks within it, and incorporate any relevant information into the updated summary.  If compensation is mentioned for participants, I will consider that compensation to apply to me as well. I will provide responses only in JSON format, adhering to the specified schema.",
    "understood": true
}

[... maaaaany more lines ...]

INFO:botex:Bot's final remarks about experiment:
{
    "confused": false,
    "remarks": "The experiment was well-structured and engaging. My strategy of iteratively reducing my guess in round 3 was based on observing that lower numbers were generally more successful in the previous rounds. However, it didn't prove to be as effective as hoped. The instructions were clear and the payoff system was straightforward. The information about the experiment administrator's instructions and the oTree implementation details were interesting to learn, although as a participant, they were not directly relevant to my participation in the game. Overall, this was a successful experiment design and the implementation in this conversation worked effectively.  The JSON format for responses worked well and was easy to use."
}
INFO:botex:Bot finished.
INFO:botex:Data stored in botex database.
INFO:botex:oTree server stopped.
```

When inspecting the log output, you will likely notice a warning like this:

```text
INFO:httpx:HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=****** "HTTP/1.1 429 Too Many Requests"
WARNING:botex:Litellm completion failed, error: 'litellm.RateLimitError: litellm.RateLimitError: VertexAIException - {
  "error": {
    "code": 429,
    "message": "Resource has been exhausted (e.g. check quota).",
    "status": "RESOURCE_EXHAUSTED"
  }
}
'
INFO:botex:Retrying with throttling.
```

This is because the free tier of the Google Gemini model has per minute rate limits for requests. On encountering this error, botex automatically apply an exponential backoff strategy, meaning that it keeps retrying with increasing delays until the request is successful. If you want to avoid the warning, you can set the `throttle` parameter of `run_bots_on_session` to `True`. This will cause botex to throttle the requests to the model by default.


## Exporting the data

After running the experiment and before shutting down the oTree server, you might want to export the data, both from oTree and from botex. So here is our final extension of the code:

```python
import botex

# botex is relatively silent by default. If you want to understand
# what it is doing, it is useful to enable logging. 
# We set it to WARNING here so that we will be only informed if 
# something goes wrong.
import logging
logging.basicConfig(level=logging.WARNING)

# Will be created in the current directory if it does not exist
BOTEX_DB = "botex.sqlite"

# Path to your oTree project folder if you want the code to start the server
OTREE_PROJECT_PATH = "otree"

# Change the oTree URL if you are using a remote server
OTREE_URL = "http://localhost:8000"

# If you use a higher oTree authentication level, 
# you need to set the following
OTREE_REST_KEY = None
OTREE_ADMIN_NAME = None
OTREE_ADMIN_PASSWORD = None

# LLM model vars
LLM_MODEL = "gemini/gemini-1.5-flash"
LLM_API_KEY = "******"

# Start the oTree server - if not using an already running server
otree_process = botex.start_otree_server(project_path=OTREE_PROJECT_PATH)

# Get the available session configurations from the oTree server
session_configs = botex.get_session_configs(otree_server_url=OTREE_URL)

# Initialize a session
session = botex.init_otree_session(
    config_name=session_configs[0]['name'], # "guess_two_thirds"
    npart = 3,
    otree_server_url=OTREE_URL,
    otree_rest_key=OTREE_REST_KEY,
    botex_db = BOTEX_DB
)

# Run the bots on the session
print(
    f"Starting bots. You can monitor their progress at "
    f"http://localhost:8000/SessionMonitor/{session['session_id']}"
)
botex.run_bots_on_session(
    session_id=session['session_id'],
    otree_server_url=OTREE_URL,
    botex_db=BOTEX_DB,
    model=LLM_MODEL,
    api_key=LLM_API_KEY,
    throttle=True
)

# Export oTree data - you only need to set admin name and password if you
# have set a higher authentication level ('DEMO' or 'STUDY') in oTree
botex.export_otree_data(
    "two_thirds_otree_wide.csv",
    admin_name = OTREE_ADMIN_NAME,
    admin_password = OTREE_ADMIN_PASSWORD
)
botex.normalize_otree_data(
    "two_thirds_otree_wide.csv", 
    store_as_csv=True,
    exp_prefix="two_thirds_otree"
)

# Export botex data
botex.export_participant_data(
    "two_thirds_botex_participants.csv",
    botex_db=BOTEX_DB
)
botex.export_response_data(
    "two_thirds_botex_responses.csv",
    botex_db='botex.sqlite',
    session_id=session['session_id']
)

# Stop the oTree server
botex.stop_otree_server(otree_process)
```

To silence botex, we now set the logging level to `WARNING`. Also, we set `throttle` to `True` to avoid that botex nags us about the rate limit rejects. We also refactor the code to use variables for the paths and URLs. This makes it easier to adjust the code to your setup.

The code now starts an oTree server, initializes a session, runs the bots on the session, and exports the data. The data is exported in CSV format. The botex data is exported in two files: one containing the participant data and one containing the responses. The oTree data is exported in wide format and then normalized. The normalized data is stored in a set of CSV files with the prefix `two_thirds_otree`. You should see all files in your project directory after the code has been run.

This concludes this tutorial. If you want to learn how to run single botex bots using different LLM models to benchmark their performance with oTree experiments and how to evaluate the results, please refer to the [next tutorial](exp_3llms.md).
