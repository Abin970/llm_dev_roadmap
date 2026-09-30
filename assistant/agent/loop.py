"""AgentLoop -- a hand-rolled ReAct loop.

Reason -> Act -> Observe, repeated: the LLM either responds with plain
text (a final answer) or asks for a tool call (an "act"); the tool's
result becomes an "observation" appended to the running message list
before calling the LLM again. A hard `max_iterations` guards against a
stuck loop -- per the roadmap's own callout, "an agent stuck re-calling
the same tool is the #1 agent production incident."

Yields Event objects (events.py), reusing Week 2's event shape, so
main.py's /research endpoint can stream progress the same way /chat was
always meant to.
"""
from __future__ import annotations

import json
from typing import Iterator

from events import Event, EventType
from llm_client import DEFAULT_MODEL, chat_with_tools
from tools.registry import ToolError, dispatch, to_openai_tools

DEFAULT_SYSTEM_PROMPT = (
    "You are a research/engineering assistant. Use the available tools "
    "when they help answer the question. When you have enough "
    "information, give your final answer directly as plain text, not a "
    "tool call."
)


class AgentLoop:
    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        max_iterations: int = 6,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self.model = model
        self.max_iterations = max_iterations
        self.system_prompt = system_prompt

    def run(self, user_message: str) -> Iterator[Event]:
        """Run the ReAct loop for one user question, yielding Events as
        it goes, ending with a COMPLETED (or ERROR) event.
        """

        messages = [
                      {"role": "developer", "content": self.system_prompt},
                      {"role": "user", "content": user_message},
                  ]
        yield Event(EventType.STARTED, {})
        tools = to_openai_tools()

        for _ in range(self.max_iterations):
            message = chat_with_tools(messages, tools, model=self.model)
            # message is the raw SDK message object -- has .content and
            # .tool_calls (see llm_client.chat_with_tools's docstring)

            print(f"Message content: {message.content}")
            if not message.tool_calls:
                yield Event(EventType.COMPLETED, {"content": message.content})
                return


            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id":tc.id,
                        "type":"function",
                        "function":{
                            "name":tc.function.name,
                            "arguments":tc.function.arguments
                        }
                    } 
                    for tc in message.tool_calls
                ]
            })

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                yield Event(EventType.TOOL_CALL, {"name": name, "args": args})
                try:
                    result = dispatch(name, args)
                except ToolError as e:
                    result = f"error:{str(e)}"
                    yield Event(EventType.ERROR, {"name": name, "message": str(e)})
                else:
                    yield Event(EventType.TOOL_RESULT, {"name": name, "result": result})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })


        yield Event(EventType.COMPLETED, {
            "content": "I wasn't able to finish within the allowed number of steps.",
        })

            
