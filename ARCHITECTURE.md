# Architecture

Forge is a natural-language interface for running real actions across three existing tools: a file organiser, an invoice generator, and a finance dashboard. It is not a chatbot that talks about those tools — it is an agent that operates them.

## Why tool use instead of a chatbot

A standard chatbot takes a question and returns text. That's fine for Q&A, but it can't actually *do* anything — it can only describe what you might do yourself.

Forge is built on Anthropic's tool use (function calling) API. Instead of just generating a text reply, Claude is given a list of real Python functions it's allowed to call — each with a name, a description, and a strict schema for its parameters. When a user types an instruction, Claude decides:

1. Whether any tool applies at all
2. Which tool (or tools, in sequence) are needed
3. What parameters to call them with

The result Claude sends back isn't a guess — it's a structured `tool_use` request. The backend then actually executes the corresponding Python function, gets a real result, and sends that result back to Claude so it can either call another tool or write a final response.

## The loop

```
user instruction
      |
      v
Claude (with tools defined) ---> decides to call a tool
      |                                    |
      |                                    v
      |                          backend executes the real function
      |                                    |
      |<---------------------------------- tool result sent back
      v
Claude either calls another tool, or writes a final answer
```

This is what allows multi-step requests to work — "check which invoices are overdue and draft a reminder for each" requires the agent to call the invoice tool first, read the result, then loop and call a message-drafting step per overdue invoice. None of that is scripted; Claude decides the sequence at runtime based on what each tool actually returns.

## Guardrails

Two rules keep this from being reckless:

- **Read-only tools execute immediately.** Querying transactions, listing invoices, previewing a file-organise run — these are safe, so they run as soon as Claude requests them.
- **Consequential tools require confirmation.** Anything that creates a file, generates a real invoice, or moves files on disk is flagged as `requires_confirmation: true`. The backend pauses, returns the proposed action to the frontend, and only executes once the user explicitly confirms.

This mirrors how a careful human assistant would behave — happy to look things up on their own, but checks before doing something that can't be easily undone.

## Tool registry

Each tool lives in its own file under `tools/`, and exposes two things: a JSON schema (for Claude) and a plain Python function (for actual execution). Adding a new capability to the agent means writing one new tool file and registering it — the orchestration logic in `agent.py` doesn't change.