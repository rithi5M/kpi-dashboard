"""Synthetic e-commerce data + KPI helpers shared by the app and the PDF export."""
import numpy as np
import pandas as pd

STATES = {
    "Tamil Nadu": (11.13, 78.66), "Karnataka": (15.32, 75.71), "Maharashtra": (19.75, 75.71),
    "Delhi": (28.70, 77.10), "Gujarat": (22.26, 71.19), "West Bengal": (22.99, 87.85),
    "Telangana": (18.11, 79.02), "Kerala": (10.85, 76.27), "Rajasthan": (27.02, 74.22),
    "Uttar Pradesh": (26.85, 80.91),
}
REGION = {
    "Tamil Nadu": "South", "Karnataka": "South", "Telangana": "South", "Kerala": "South",
    "Maharashtra": "West", "Gujarat": "West", "Rajasthan": "West",
    "Delhi": "North", "Uttar Pradesh": "North", "West Bengal": "East",
}
CATEGORIES = ["Apparel", "Electronics", "Home & Living", "Beauty", "Grocery"]
CHANNELS = ["Organic", "Paid Search", "Social", "Email", "Referral"]
CAC_BASE = {"Organic": 0, "Paid Search": 520, "Social": 410, "Email": 120, "Referral": 200}


def make_data(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    months = pd.date_range("2024-01-01", "2025-12-01", freq="MS")
    rows = []
    for m_i, month in enumerate(months):
        season = 1 + 0.25 * np.sin((month.month - 3) / 12 * 2 * np.pi) + (0.35 if month.month in (10, 11) else 0)
        growth = 1 + 0.025 * m_i
        for state in STATES:
            size = {"Tamil Nadu": 1.4, "Maharashtra": 1.5, "Karnataka": 1.3, "Delhi": 1.2}.get(state, 0.8)
            for cat in CATEGORIES:
                for ch in CHANNELS:
                    orders = max(int(rng.normal(40, 8) * size * season * growth), 1)
                    aov = rng.normal({"Apparel": 1800, "Electronics": 5200, "Home & Living": 2600,
                                      "Beauty": 950, "Grocery": 700}[cat], 120)
                    new_cust = int(orders * rng.uniform(0.25, 0.45))
                    cac_spend = new_cust * CAC_BASE[ch] * rng.uniform(0.85, 1.15)
                    start_cust = int(orders * rng.uniform(1.8, 2.4))
                    churned = int(start_cust * rng.uniform(0.03, 0.07) * (1.1 - 0.0 * m_i))
                    rows.append((month, state, REGION[state], cat, ch, orders, orders * aov,
                                 new_cust, cac_spend, start_cust, churned))
    df = pd.DataFrame(rows, columns=["month", "state", "region", "category", "channel", "orders",
                                      "revenue", "new_customers", "acq_spend", "start_customers", "churned"])
    df["lat"] = df["state"].map(lambda s: STATES[s][0])
    df["lon"] = df["state"].map(lambda s: STATES[s][1])
    return df


def kpis(d: pd.DataFrame) -> dict:
    rev = d["revenue"].sum()
    orders = d["orders"].sum()
    new_c = d["new_customers"].sum()
    return {
        "revenue": rev,
        "cac": d["acq_spend"].sum() / new_c if new_c else 0.0,
        "churn": d["churned"].sum() / d["start_customers"].sum() * 100 if d["start_customers"].sum() else 0.0,
        "aov": rev / orders if orders else 0.0,
    }


def fmt_inr(x: float) -> str:
    if x >= 1e7:
        return f"₹{x/1e7:.2f} Cr"
    if x >= 1e5:
        return f"₹{x/1e5:.2f} L"
    return f"₹{x:,.0f}"
