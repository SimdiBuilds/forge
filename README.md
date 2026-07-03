# Forge

A natural-language interface that operates real tools instead of just chatting about them. Ask it to create an invoice, check your finances, or organise a folder, and it actually does it — using Claude's tool use API to decide what to run and executing real Python functions underneath.

> 🚧 Work in progress. See [ARCHITECTURE.md](./ARCHITECTURE.md) for the design.

**Stack:** Python · FastAPI · Anthropic API (tool use) · pandas · reportlab