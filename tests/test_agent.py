from unittest.mock import patch

import agent


class FakeBlock:
    """Mimics an Anthropic content block (text or tool_use)."""
    def __init__(self, type_, **kwargs):
        self.type = type_
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeResponse:
    """Mimics an Anthropic Messages API response."""
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


def test_final_text_response_no_tools_needed():
    fake_response = FakeResponse(
        content=[FakeBlock("text", text="Hello, how can I help?")],
        stop_reason="end_turn",
    )
    with patch.object(agent.client.messages, "create", return_value=fake_response):
        result = agent.run_turn("hi", [])

    assert result["type"] == "final"
    assert result["text"] == "Hello, how can I help?"
    assert result["pending_confirmations"] == []


def test_read_only_tool_executes_immediately():
    tool_call = FakeResponse(
        content=[FakeBlock("tool_use", id="tool_1", name="get_finance_summary", input={})],
        stop_reason="tool_use",
    )
    final = FakeResponse(
        content=[FakeBlock("text", text="Your net balance is $11,836.66.")],
        stop_reason="end_turn",
    )

    with patch.object(agent.client.messages, "create", side_effect=[tool_call, final]):
        result = agent.run_turn("what's my balance?", [])

    assert result["type"] == "final"
    assert "11,836.66" in result["text"] or result["text"] == "Your net balance is $11,836.66."
    assert len(result["trace"]) == 1
    assert result["trace"][0]["tool_name"] == "get_finance_summary"


def test_consequential_tool_requires_confirmation():
    tool_call = FakeResponse(
        content=[FakeBlock(
            "tool_use", id="tool_2", name="create_invoice",
            input={"client_name": "Acme Corp", "items": [{"description": "Design", "quantity": 1, "unit_price": 500}]},
        )],
        stop_reason="tool_use",
    )
    acknowledgement = FakeResponse(
        content=[FakeBlock("text", text="I'm ready to create that invoice — just confirm to proceed.")],
        stop_reason="end_turn",
    )

    with patch.object(agent.client.messages, "create", side_effect=[tool_call, acknowledgement]):
        result = agent.run_turn("create an invoice for Acme Corp for $500 design work", [])

    assert result["type"] == "confirmation_required"
    assert len(result["pending_confirmations"]) == 1
    assert result["pending_confirmations"][0]["tool_name"] == "create_invoice"
    # nothing should have actually run yet
    assert result["trace"] == []


def test_confirm_action_actually_executes_and_responds():
    acknowledgement = FakeResponse(
        content=[FakeBlock("text", text="Done — invoice created and ready for you.")],
        stop_reason="end_turn",
    )

    with patch.object(agent.client.messages, "create", return_value=acknowledgement):
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
    first_call = FakeResponse(
        content=[FakeBlock("tool_use", id="t1", name="get_finance_summary", input={})],
        stop_reason="tool_use",
    )
    second_call = FakeResponse(
        content=[FakeBlock("tool_use", id="t2", name="get_spending_by_category", input={})],
        stop_reason="tool_use",
    )
    final = FakeResponse(
        content=[FakeBlock("text", text="Your biggest expense category is Housing.")],
        stop_reason="end_turn",
    )

    with patch.object(agent.client.messages, "create", side_effect=[first_call, second_call, final]):
        result = agent.run_turn("what's my balance and biggest expense category?", [])

    assert result["type"] == "final"
    assert len(result["trace"]) == 2
    tool_names = [t["tool_name"] for t in result["trace"]]
    assert "get_finance_summary" in tool_names
    assert "get_spending_by_category" in tool_names