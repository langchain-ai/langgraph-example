// How to create agents with configuration
import { Client } from "@langchain/langgraph-sdk";

/*
One of the benefits of LangGraph API is that it lets you create agents with different configurations.
This is useful when you want to:

- Define a cognitive architecture once as a LangGraph
- Let that LangGraph be configurable across some attributes (for example, system message or LLM to use)
- Let users create agents with arbitrary configurations, save them, and then use them in the future

In this guide we will show how to do that for the default agent we have built in.

If you look at the agent we defined, you can see that inside the `call_model` node we have created the model based on some configuration. That node looks like:

```python
def call_model(state, config):
    messages = state["messages"]
    model_name = config.get('configurable', {}).get("model_name", "anthropic")
    model = _get_model(model_name)
    response = model.invoke(messages)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}
```

We are looking inside the config for a `model_name` parameter (which defaults to `anthropic` if none is found).
That means that by default we are using Anthropic as our model provider.
In this example we will see an example of how to create an example agent that is configured to use OpenAI.
*/

async function main() {
  const client = new Client();
  const assistant = await client.assistants.create({
    graphId: "agent",
    config: { configurable: { model_name: "openai" } },
  });
  // We can see that this assistant has saved the config
  console.log("Assistant", assistant);
  const thread = await client.threads.create();
  const input = { messages: [{ role: "user", content: "who made you?" }] };

  for await (const event of client.runs.stream(
    thread.thread_id,
    assistant.assistant_id,
    { input }
  )) {
    console.log(`Receiving new event of type: ${event.event}...`);
    console.log(JSON.stringify(event.data));
    console.log("\n\n");
  }
}

main();
