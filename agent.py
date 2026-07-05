import json
import os

import anthropic

from tools.registry import CLAUDE_TOOLS, TOOL_META

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = (
    "You are Forge, an assistant that operates real tools on the user's behalf: "
    "organising files, creating invoices, and answering questions about their "
    "finances. Use the tools available to you whenever the request calls for one. "
    "If a request needs more than one tool, call them one at a time and use each "
    "result to decide the next step. Keep your final responses short and direct."
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
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=CLAUDE_TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            final_text = "".join(b.text for b in response.content if b.type == "text")
            return {"type": "final", "text": final_text, "pending_confirmations": [], "trace": full_trace, "history": messages}

        tool_results = []
        pending = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            meta = TOOL_META[block.name]

            if meta["requires_confirmation"]:
                pending.append({
                    "tool_use_id": block.id,
                    "tool_name": block.name,
                    "tool_input": block.input,
                })
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"status": "awaiting user confirmation, not yet executed"}),
                })
            else:
                result = meta["executor"](**block.input)
                full_trace.append({"tool_name": block.name, "tool_input": block.input, "result": result})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

        messages.append({"role": "user", "content": tool_results})

        if pending:
            # Let Claude acknowledge what's pending in plain language, then
            # stop here — the real execution waits for an explicit confirm.
            response = client.messages.create(
                model=MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                tools=CLAUDE_TOOLS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})
            final_text = "".join(b.text for b in response.content if b.type == "text")
            return {
                "type": "confirmation_required",
                "text": final_text or "This action needs your confirmation before I proceed.",
                "pending_confirmations": pending,
                "trace": full_trace,
                "history": messages,
            }

        # No pending confirmations — loop again in case Claude wants to
        # call another tool based on what it just learned.


def confirm_action(tool_name: str, tool_input: dict, history: list[dict]) -> dict:
    """Actually run a tool that was previously held for confirmation."""
    meta = TOOL_META[tool_name]
    result = meta["executor"](**tool_input)

    note = f"The {tool_name} action was confirmed and executed. Result: {json.dumps(result)}"
    messages = history + [{"role": "user", "content": note}]

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        tools=CLAUDE_TOOLS,
        messages=messages,
    )
    messages.append({"role": "assistant", "content": response.content})
    final_text = "".join(b.text for b in response.content if b.type == "text")

    return {"type": "final", "text": final_text, "result": result, "history": messages}