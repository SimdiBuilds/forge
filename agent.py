import json
import os

from openai import OpenAI

from tools.registry import GROQ_TOOLS, TOOL_META

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY") or "not-set",
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = (
    "You are Forge, an assistant that operates real tools on the user's behalf: "
    "organising files, creating invoices, and answering questions about their "
    "finances. Use the tools available to you whenever the request calls for one. "
    "If a request needs more than one tool, call them one at a time and use each "
    "result to decide the next step. Keep your final responses short and direct."
)


def _call_model(messages: list[dict]):
    return client.chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        tools=GROQ_TOOLS,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
    )


def run_turn(user_message: str, history: list[dict]) -> dict:
    """
    Send one user instruction through the agent loop. Read-only tools execute
    immediately; tools that require confirmation are paused and returned to
    the caller instead of being run.
    """
    messages = history + [{"role": "user", "content": user_message}]
    full_trace = []

    while True:
        response = _call_model(messages)
        message = response.choices[0].message

        assistant_entry = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ]
        messages.append(assistant_entry)

        if not message.tool_calls:
            return {
                "type": "final",
                "text": message.content or "",
                "pending_confirmations": [],
                "trace": full_trace,
                "history": messages,
            }

        pending = []

        for tc in message.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            meta = TOOL_META[name]

            if meta["requires_confirmation"]:
                pending.append({"tool_call_id": tc.id, "tool_name": name, "tool_input": args})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"status": "awaiting user confirmation, not yet executed"}),
                })
            else:
                result = meta["executor"](**args)
                full_trace.append({"tool_name": name, "tool_input": args, "result": result})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        if pending:
            # Let the model acknowledge what's pending in plain language,
            # then stop here — real execution waits for an explicit confirm.
            response = _call_model(messages)
            ack = response.choices[0].message
            messages.append({"role": "assistant", "content": ack.content or ""})
            return {
                "type": "confirmation_required",
                "text": ack.content or "This action needs your confirmation before I proceed.",
                "pending_confirmations": pending,
                "trace": full_trace,
                "history": messages,
            }

        # No pending confirmations — loop again in case the model wants to
        # call another tool based on what it just learned.


def confirm_action(tool_name: str, tool_input: dict, history: list[dict]) -> dict:
    """Actually run a tool that was previously held for confirmation."""
    meta = TOOL_META[tool_name]
    result = meta["executor"](**tool_input)

    note = f"The {tool_name} action was confirmed and executed. Result: {json.dumps(result)}"
    messages = history + [{"role": "user", "content": note}]

    response = _call_model(messages)
    message = response.choices[0].message
    messages.append({"role": "assistant", "content": message.content or ""})

    return {"type": "final", "text": message.content or "", "result": result, "history": messages}