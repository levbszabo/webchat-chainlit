"""
Simple demo of integration with ChainLit and LangGraph.
"""

from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import chainlit as cl
import operator
from chainlit.message import AskUserMessage
from langchain_community.tools import WriteFileTool
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
from langgraph.prebuilt import ToolNode, tools_condition
from tool_kit import CalendarBookingTool
from prompts import acquisition_prompt
from fetch_secrets import get_secret
import os

local = True
secrets = get_secret(local)

# Set the secrets as environment variables
if not local:  # you will have these in the environment variables
    for key, value in secrets.items():
        os.environ[key] = value
# Initialize tools
calendar_tool = CalendarBookingTool()
tools = [calendar_tool]


class ChatState(TypedDict):
    messages: Annotated[Sequence[AnyMessage], operator.add]
    # quote_info: Annotated[Sequence[AnyMessage], operator.add]


# planner_response: Annotated[list, add_messages]


@cl.step
async def chat_node(state: ChatState, config: RunnableConfig) -> ChatState:
    # Get the current date and format it as needed in EST
    EST = ZoneInfo("America/New_York")
    current_date = datetime.now(EST).strftime("%Y-%m-%d %I:%M %p")

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=acquisition_prompt.format(current_date=current_date)),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    llm = ChatOpenAI(model="gpt-4o", streaming=True)
    llm_with_tools = llm.bind_tools(tools)
    chain: Runnable = prompt | llm_with_tools
    response = await chain.ainvoke(state, config=config)
    new_state = {"messages": state["messages"] + [response]}
    return new_state


@cl.on_chat_start
async def on_chat_start():
    # Check if we have user info stored in the session
    user_info = cl.user_session.get("user_info", {"name": None, "email": None})
    if user_info["name"] and user_info["email"]:
        # We already have the user's info, greet them and continue
        await cl.Message(
            content=f"Welcome back, {user_info['name']}! How can we assist your business today?"
        ).send()
    else:
        # Initial Introduction and User Information Collection
        initial_message = cl.Message(
            content="""Welcome to Journeyman AI! We offer a range of AI solutions including:
        1. AI Sales Agents
        2. Asynchronous Discovery Tools
        3. SMS Marketing
        4. Customer Segmentation
        5. AI Tools trained on internal data
        6. Recommendation Systems
        7. Custom AI Solutions
        """
        )
        await initial_message.send()

        res_name = await AskUserMessage(content="Please enter your name:").send()
        if res_name:
            user_info["name"] = res_name["output"]

        res_email = await AskUserMessage(content="Please enter your email:").send()
        if res_email:
            user_info["email"] = res_email["output"]

        # Save user info in the session
        cl.user_session.set("user_info", user_info)

        # Ask about service interest or business needs
        follow_message = "Is there any particular service you are interested in, or could you tell us more about your business and what issues you are facing?"
        await cl.Message(content=follow_message).send()

    # Start graph
    graph = StateGraph(ChatState)

    graph.add_node("chat", chat_node)
    tool_node = ToolNode(tools=tools)
    graph.add_node("tools", tool_node)
    graph.add_conditional_edges("chat", tools_condition)
    graph.add_edge("tools", "chat")
    graph.add_edge("chat", END)
    graph.set_entry_point("chat")

    graph_runnable = graph.compile()
    # Initialize state
    state = ChatState(
        messages=[
            AIMessage(content=initial_message.content),
            HumanMessage(content=f"My name is {user_info['name']}"),
            HumanMessage(content=f"My email is {user_info['email']}"),
            AIMessage(content=follow_message),
        ]
    )
    # print("Initial state:", state)  # Debug print

    # Save graph and state to the user session
    cl.user_session.set("graph", graph_runnable)
    cl.user_session.set("state", state)


@cl.on_message
async def on_message(message: cl.Message):
    # Retrieve the graph and state from the user session
    graph: Runnable = cl.user_session.get("graph")
    state = cl.user_session.get("state")
    # print("State before receiving message:", state)  # Debug print

    # Append the new message to the state
    state["messages"] += [HumanMessage(content=message.content)]

    # print("State after receiving
    # # message:", state)  # Debug print

    # Stream the response to the UI if all information is collected
    ui_message = cl.Message(content="")
    await ui_message.send()

    # Initialize an empty string to accumulate the response content
    response_content = ""

    async for event in graph.astream_events(state, version="v1"):
        if event["event"] == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            response_content += content  # Accumulate the content
            await ui_message.stream_token(token=content)

    # Update the ui_message content with the accumulated response content
    ui_message.content = response_content
    await ui_message.update()

    # Add the AI's response to the state
    state["messages"] += [AIMessage(content=ui_message.content)]
    print("hello!")
    # Save the updated state back to the user session
    cl.user_session.set("state", state)


if __name__ == "__acquisition__":
    from chainlit.cli import run_chainlit

    run_chainlit(__file__)
