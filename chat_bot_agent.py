from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from typing import Annotated
import re
from typing_extensions import TypedDict
from langchain_community.agent_toolkits.github.toolkit import GitHubToolkit
from langchain_community.utilities.github import GitHubAPIWrapper
from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.tools import BaseTool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from typing import Optional
import requests
import time
import jwt
import os

# Utilities - TODO: Move to Utils folder
app_id = '903588'
installation_id = '51026556'
private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY_1")

def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }

def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )

def _print_event(event: dict, _printed: set, max_length=1500):
    current_state = event.get("dialog_state")
    if current_state:
        print(f"Currently in: ", current_state[-1])
    message = event.get("messages")
    if message:
        if isinstance(message, list):
            message = message[-1]
        if message.id not in _printed:
            msg_repr = message.pretty_repr(html=True)
            if len(msg_repr) > max_length:
                msg_repr = msg_repr[:max_length] + " ... (truncated)"
            print(msg_repr)
            _printed.add(message.id)

def convert_tools_name(tools) -> list[BaseTool]:
	for tool in tools:
		input_string = tool.name.lower()
		cleaned_string = re.sub(r'[^a-zA-Z0-9_-]+', ' ', input_string)
		tool.name = re.sub(r'\s+', '_', cleaned_string).strip('_')
	return tools

def generate_jwt(app_id, private_key):
    payload = {
        'iat': int(time.time()),
        'exp': int(time.time()) + (10 * 60),  # JWT expiration time (10 minutes)
        'iss': app_id
    }
    encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256')
    return encoded_jwt

def get_installation_access_token(app_id, private_key, installation_id):
    jwt_token = generate_jwt(app_id, private_key)
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
    response = requests.post(url, headers=headers)
    response_data = response.json()
    return response_data['token']

def list_repo_contents(owner, repo, path, access_token):
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    response = requests.get(url, headers=headers)
    return response.json()

def list_all_files(owner, repo, path='', access_token=None, files=[]):
    contents = list_repo_contents(owner, repo, path, access_token)
    for item in contents:
        if item['type'] == 'file':
            files.append(item['path'])
        elif item['type'] == 'dir':
            list_all_files(owner, repo, item['path'], access_token, files)

access_token = get_installation_access_token(app_id, private_key, installation_id)

@tool
def github_fetch_files_from_repo(repo: Optional[str] = None) -> list[str]:
	"""
	List all the files in a given repo

	Args:
      repo (Optional[str]): repository name
	Returns:
      List[str]: List of files from the repository
	"""
	owner = 'ekline-io'
	repo = 'documentation'
	path = ''  # Root directory or specify a subdirectory
	files = []
	list_all_files(owner, repo, path, access_token, files)
	return files


searchTool = TavilySearchResults(max_results=1)
class State(TypedDict):
	messages: Annotated[list[AnyMessage], add_messages]

class Assistant:
	def __init__(self, runnable: Runnable):
		self.runnable = runnable

	def __call__(self, state: State, config: RunnableConfig):
		while True:
			issues = config.get("issues", None)
			state = {**state, "issues": issues}
			result = self.runnable.invoke(state)
			# If the LLM happens to return an empty response, we will re-prompt it
			# for an actual response.
			if not result.tool_calls and (
				not result.content
				or isinstance(result.content, list)
				and not result.content[0].get("text")
			):
				messages = state["messages"] + [("user", "Respond with a real output.")]
				state = {**state, "messages": messages}
			else:
				break
		return {"messages": result}


# Haiku is faster and cheaper, but less accurate
# llm = ChatAnthropic(model="claude-3-haiku-20240307")
llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=1)
# You could swap LLMs, though you will likely want to update the prompts when
# doing so!
# from langchain_openai import ChatOpenAI

# llm = ChatOpenAI(model="gpt-4-turbo-preview")

primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
			(
				"system",
				"You are a helpful support assistant for ekline, the company, products. "
				" Use the provided github tools that can search for issues, comments on issues, solve issues, create PRs in a repositories to assist the user's queries. "
				" When searching, be persistent. Expand your query bounds if the first search returns no results. "
				" If a search comes up empty, expand your search before giving up."
			),
			("placeholder", "{messages}")
    ]
)

part_1_tools = [searchTool , github_fetch_files_from_repo]
part_1_assistant_runnable = primary_assistant_prompt | llm.bind_tools(part_1_tools)

builder = StateGraph(State)


# Define nodes: these do the work
builder.add_node("assistant", Assistant(part_1_assistant_runnable))
builder.add_node("tools", create_tool_node_with_fallback(part_1_tools))
# Define edges: these determine how the control flow moves
builder.set_entry_point("assistant")
builder.add_conditional_edges(
    "assistant",
    tools_condition,
)
builder.add_edge("tools", "assistant")

# The checkpointer lets the graph persist its state
# this is a complete memory for the entire graph.
memory = SqliteSaver.from_conn_string(":memory:")
part_1_graph = builder.compile(checkpointer=memory)


# # Let's create an example conversation a user might have with the assistant
# tutorial_questions = [
#     "How many open issues are present in the repository",
# ]

# thread_id = str(uuid.uuid4())

# config = {
# 	"configurable": {
# 		# Checkpoints are accessed by thread_id
# 		"thread_id": thread_id,
# 		"issues": github.get_issues()
# 	}
# }
# # print(part_1_graph.get_state(config=config))

# _printed = set()
# for question in tutorial_questions:
# 	events = part_1_graph.stream(
# 		{"messages": ("user", question)}, config, stream_mode="values"
# 	)
# 	for event in events:
# 		_print_event(event, _printed)