from unittest.mock import patch

import agent


class FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, id_, name, arguments):
        self.id = id_
        self.function = FakeFunction(name, arguments)


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeChoice:
    def __init__(self, message):
        self.message = message


class FakeResponse:
    def __init__(self, message):
        self.choices = [FakeChoice(message)]


def test_final_text_response_no_tools_needed():
    fake = FakeResponse(FakeMessage(content="Hello, how can I help?"))
    with patch.object(agent.client.chat.completions, "create", return_value=fake):
        result = agent.run_turn("hi", [])

    assert result["type"] == "final"
    assert result["text"] == "Hello, how can I help?"
    assert result["pending_confirmations"] == []


def test_read_only_tool_executes_immediately():
    tool_call = FakeResponse(FakeMessage(
        tool_calls=[FakeToolCall("call_1", "get_finance_summary", "{}")]
    ))
    final = FakeResponse(FakeMessage(content="Your net balance is $11,836.66."))

    with patch.object(agent.client.chat.completions, "create", side_effect=[tool_call, final]):
        result = agent.run_turn("what's my balance?", [])

    assert result["type"] == "final"
    assert len(result["trace"]) == 1
    assert result["trace"][0]["tool_name"] == "get_finance_summary"


def test_consequential_tool_requires_confirmation():
    args = '{"client_name": "Acme Corp", "items": [{"description": "Design", "quantity": 1, "unit_price": 500}]}'
    tool_call = FakeResponse(FakeMessage(
        tool_calls=[FakeToolCall("call_2", "create_invoice", args)]
    ))
    ack = FakeResponse(FakeMessage(content="I'm ready to create that invoice — just confirm to proceed."))

    with patch.object(agent.client.chat.completions, "create", side_effect=[tool_call, ack]):
        result = agent.run_turn("create an invoice for Acme Corp for $500 design work", [])

    assert result["type"] == "confirmation_required"
    assert len(result["pending_confirmations"]) == 1
    assert result["pending_confirmations"][0]["tool_name"] == "create_invoice"
    assert result["trace"] == []


def test_confirm_action_actually_executes_and_responds():
    ack = FakeResponse(FakeMessage(content="Done — invoice created and ready for you."))

    with patch.object(agent.client.chat.completions, "create", return_value=ack):
        result = agent.confirm_action(
            "create_invoice",
            {"client_name": "Acme Corp", "items": [{"description": "Design", "quantity": 1, "unit_price": 500}]},
            [],
        )

    assert result["type"] == "final"
    assert result["result"]["client_name"] == "Acme Corp"
    assert result["result"]["total"] == 500.0
    assert "file_path" in result["result"]


def test_multi_step_chaining_calls_two_tools_in_sequence():
    first = FakeResponse(FakeMessage(tool_calls=[FakeToolCall("t1", "get_finance_summary", "{}")]))
    second = FakeResponse(FakeMessage(tool_calls=[FakeToolCall("t2", "get_spending_by_category", "{}")]))
    final = FakeResponse(FakeMessage(content="Your biggest expense category is Housing."))

    with patch.object(agent.client.chat.completions, "create", side_effect=[first, second, final]):
        result = agent.run_turn("what's my balance and biggest expense category?", [])

    assert result["type"] == "final"
    assert len(result["trace"]) == 2
    tool_names = [t["tool_name"] for t in result["trace"]]
    assert "get_finance_summary" in tool_names
    assert "get_spending_by_category" in tool_names