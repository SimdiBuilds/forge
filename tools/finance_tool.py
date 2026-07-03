from collections import defaultdict
from pathlib import Path

import pandas as pd

SAMPLE_PATH = Path("sample_data/transactions.csv")

CATEGORY_RULES = {
    "Food & Dining": ["restaurant", "cafe", "coffee", "mcdonald", "kfc", "pizza",
                      "grocery", "supermarket", "starbucks", "doordash", "ubereats"],
    "Transport": ["uber", "lyft", "taxi", "fuel", "parking", "toll", "flight"],
    "Shopping": ["amazon", "walmart", "target", "store", "shop"],
    "Entertainment": ["netflix", "spotify", "cinema", "movie", "game", "steam", "concert"],
    "Utilities": ["electricity", "water", "internet", "bill", "power"],
    "Health": ["pharmacy", "hospital", "clinic", "doctor", "gym", "medical"],
    "Housing": ["rent", "mortgage", "landlord"],
    "Income": ["salary", "payroll", "deposit", "freelance", "cashback"],
}

FINANCE_SUMMARY_SCHEMA = {
    "name": "get_finance_summary",
    "description": "Get total income, total expenses, and net balance from the loaded transaction data. Read-only, safe to call anytime.",
    "input_schema": {"type": "object", "properties": {}},
    "requires_confirmation": False,
}

FINANCE_BY_CATEGORY_SCHEMA = {
    "name": "get_spending_by_category",
    "description": "Get total spending broken down by category (Food, Transport, Housing, etc). Read-only, safe to call anytime.",
    "input_schema": {"type": "object", "properties": {}},
    "requires_confirmation": False,
}


def _categorise(description: str) -> str:
    desc = description.lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(kw in desc for kw in keywords):
            return category
    return "Other"


def _load_transactions() -> pd.DataFrame:
    df = pd.read_csv(SAMPLE_PATH)
    df.columns = [c.strip().lower() for c in df.columns]
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    if "type" not in df.columns:
        df["type"] = df["amount"].apply(lambda x: "income" if x > 0 else "expense")
    df["category"] = df["description"].apply(_categorise)
    df["amount"] = df["amount"].abs()
    return df


def get_finance_summary() -> dict:
    df = _load_transactions()
    income = df[df["type"] == "income"]["amount"].sum()
    expenses = df[df["type"] == "expense"]["amount"].sum()
    return {
        "total_income": round(float(income), 2),
        "total_expenses": round(float(expenses), 2),
        "net_balance": round(float(income - expenses), 2),
        "transaction_count": len(df),
    }


def get_spending_by_category() -> dict:
    df = _load_transactions()
    expenses = df[df["type"] == "expense"]
    totals = defaultdict(float)
    for _, row in expenses.iterrows():
        totals[row["category"]] += row["amount"]

    breakdown = sorted(
        [{"category": cat, "total": round(amt, 2)} for cat, amt in totals.items()],
        key=lambda x: x["total"],
        reverse=True,
    )
    return {"by_category": breakdown}