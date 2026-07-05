from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agent import run_turn, confirm_action

app = FastAPI(title="Forge")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

_session_history: list[dict] = []


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/agent/message")
async def agent_message(payload: dict):
    message = payload.get("message", "")
    result = run_turn(message, _session_history)
    _session_history[:] = result["history"]
    return {
        "type": result["type"],
        "text": result.get("text", ""),
        "pending_confirmations": result.get("pending_confirmations", []),
        "trace": result.get("trace", []),
    }


@app.post("/agent/confirm")
async def agent_confirm(payload: dict):
    tool_name = payload["tool_name"]
    tool_input = payload["tool_input"]
    result = confirm_action(tool_name, tool_input, _session_history)
    _session_history[:] = result["history"]
    return {"type": "final", "text": result["text"], "result": result["result"]}