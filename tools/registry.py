from tools.file_tool import FILE_TOOL_SCHEMA, organise_files
from tools.invoice_tool import INVOICE_TOOL_SCHEMA, create_invoice
from tools.finance_tool import (
    FINANCE_SUMMARY_SCHEMA,
    FINANCE_BY_CATEGORY_SCHEMA,
    get_finance_summary,
    get_spending_by_category,
)

_RAW_TOOLS = [
    (FILE_TOOL_SCHEMA, organise_files),
    (INVOICE_TOOL_SCHEMA, create_invoice),
    (FINANCE_SUMMARY_SCHEMA, get_finance_summary),
    (FINANCE_BY_CATEGORY_SCHEMA, get_spending_by_category),
]

GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema["input_schema"],
        },
    }
    for schema, _ in _RAW_TOOLS
]

TOOL_META = {
    schema["name"]: {
        "executor": fn,
        "requires_confirmation": schema.get("requires_confirmation", False),
    }
    for schema, fn in _RAW_TOOLS
}