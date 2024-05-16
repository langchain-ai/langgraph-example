# `langgraph-api`

This is an example of how to use `langgraph-api` to stand up a REST API for your custom LangGraph StateGraph. This API can be used to interact with your StateGraph from any programming language that can make HTTP requests.

[LangGraph](https://github.com/langchain-ai/langgraph) is a library for building stateful, multi-actor applications with LLMs. The main use cases for LangGraph are conversational agents, and long-running, multi-step LLM applications or any LLM application that would benefit from built-in support for persistent checkpoints, cycles and human-in-the-loop interactions (ie. LLM and human collaboration).

`langgraph-api` shortens the time-to-market for developers using LangGraph, with a one-liner command to start a production-ready HTTP microservice for your LangGraph applications, with built-in persistence. This lets you focus on the logic of your LangGraph graph, and leave the scaling and API design to us. The API is inspired by the OpenAI assistants API, and is designed to fit in alongside your existing services.

## API Features

It has the following features:

- saved assistants, tracking config for your graphs
- saved threads, tracking state/conversation history
- human in the loop endpoints (interrupt a run, authorize nodes, get thread state, update thread state, get history of past thread states)
- streaming runs (with multiple stream formats, including token-by-token messages, state values and node updates)
- background runs (with api for checking status and events, and support for completion webhooks)

We've designed it as a robust server you can run in production at high scale, and also easily test locally.

## Getting started

This project uses `poetry` for dependency management and packaging in Python.

1. Make sure python3 and pip3 are install and available in your PATH. 
2. Install pipx `python3 -m pip install --user pipx`
3. Install [poetry](https://python-poetry.org/docs/#system-requirements) `pipx install poetry`
4. Run `poetry install` to install all the dependencies

`poetry` creates virtual environment in {cache-dir/virtualenvs}. Refer this [doc](https://python-poetry.org/docs/configuration/#cache-dir)


First, install the `langgraph-cli` package:

```bash
pip install langgraph-cli
```

Then, create a `langgraph.json` file with your configuration. You can declare local and external python dependencies (which will be installed with `pip`), env vars (or an env file) and the path to your StateGraph. You can expose multiple StateGraphs in the same API server by providing multiple paths. Here's an example:

```json
{
  "dependencies": [
    "langchain_community",
    "langchain_anthropic",
    "langchain_openai",
    "wikipedia",
    "scikit-learn",
    "./my_graphs"
  ],
  "graphs": {
    "agent": "./my_graphs/agent.py:graph"
  },
  "env": ".env"
}
```

In the `graphs` mapping, the key is the `graph_id` and the value is the path to the StateGraph. The `graph_id` is used in the API when creating an assistant.

The `env` field can be a path to an env file or a dictionary of environment variables. These environment variables will be available to your LangGraph code.

Then, run the following command to start the API server:

```bash
langgraph up
```

This will start the API server on `http://localhost:8123`. You can now interact with your StateGraph using the API or SDK.

If you're calling this API from Python, you might want to use the `langgraph-sdk` package, which provides a Python client for this API.

## API Reference

The API reference is available at `http://localhost:8123/docs` when running locally. You can preview it here: [API Reference](https://langchain-ai.github.io/langgraph-example/).

## Using the API

The API is designed to be easy to use from any programming language. Here's an example of how to use it from Python:

```python
from langgraph_sdk import get_client

client = get_client()

# List all assistants
assistants = await client.assistants.search()
# We auto-create an assistant for each graph you register in config.

agent = assistants[0]

# Start a new thread
thread = await client.threads.create()

# Start a streaming run
input = {"messages": [{"role": "human", "content": "whats the weather in la"}]}
async for chunk in client.runs.stream(thread['thread_id'], agent['assistant_id'], input=input):
    print(chunk)

# Start a background run
input = {"messages": [{"role": "human", "content": "and in sf"}]}
run = await client.runs.create(thread['thread_id'], assistant["assistant_id"], input=input)
```

See more in `notebooks/agent.ipynb`
