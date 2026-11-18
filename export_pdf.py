"""Exports the dashboard (all data, no filters) as a one-page PDF."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from data_gen import make_data, kpis, fmt_inr, CATEGORIES

df = make_data()
k = kpis(df)
cur = df[df["month"].dt.year == 2025]
prev = df[df["month"].dt.year == 2024]
kc, kp = kpis(cur), kpis(prev)


def chg(key):
    return (kc[key] - kp[key]) / kp[key] * 100


fig = plt.figure(figsize=(16.5, 11.7))  # A3 landscape-ish
fig.patch.set_facecolor("#faf8f3")
fig.text(0.04, 0.955, "Executive KPI Dashboard", fontsize=26, fontweight="bold", color="#111827")
fig.text(0.04, 0.93, "Jan 2024 – Dec 2025  |  synthetic e-commerce data, India  |  all regions, categories, channels",
         fontsize=11, color="#6b7280")

cards = [
    ("REVENUE", fmt_inr(k["revenue"]), chg("revenue"), False),
    ("CUSTOMER ACQUISITION COST", f"₹{k['cac']:,.0f}", chg("cac"), True),
    ("CHURN RATE", f"{k['churn']:.2f}%", chg("churn"), True),
    ("AVERAGE ORDER VALUE", f"₹{k['aov']:,.0f}", chg("aov"), False),
]
for i, (label, val, c, inv) in enumerate(cards):
    ax = fig.add_axes([0.04 + i * 0.235, 0.80, 0.22, 0.10])
    ax.set_facecolor("white")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#e6e6ea")
    good = (c < 0) if inv else (c > 0)
    ax.text(0.05, 0.75, label, fontsize=9, color="#6b7280", transform=ax.transAxes)
    ax.text(0.05, 0.35, val, fontsize=22, fontweight="bold", color="#111827", transform=ax.transAxes)
    ax.text(0.65, 0.38, f"{'▲' if c > 0 else '▼'} {abs(c):.1f}% vs 2024", fontsize=9,
            color="#16a34a" if good else "#dc2626", transform=ax.transAxes)

# Revenue area trend by category
ax1 = fig.add_axes([0.05, 0.48, 0.52, 0.27])
t = df.pivot_table(index="month", columns="category", values="revenue", aggfunc="sum")[CATEGORIES] / 1e7
ax1.stackplot(t.index, t.T.values, labels=CATEGORIES, colors=["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854"])
ax1.set_title("Monthly revenue by category (₹ Cr)", loc="left", fontsize=12, fontweight="bold")
ax1.legend(ncol=5, loc="upper left", fontsize=8, frameon=False)
ax1.spines[["top", "right"]].set_visible(False)

# CAC vs churn by channel
ax2 = fig.add_axes([0.64, 0.48, 0.32, 0.27])
ch = df.groupby("channel").apply(lambda d: pd.Series({
    "cac": d["acq_spend"].sum() / d["new_customers"].sum(),
    "churn": d["churned"].sum() / d["start_customers"].sum() * 100,
    "rev": d["revenue"].sum()}), include_groups=False)
ax2.scatter(ch["cac"], ch["churn"], s=ch["rev"] / ch["rev"].max() * 1500, alpha=.7, color="#fc8d62")
for name, r in ch.iterrows():
    ax2.annotate(name, (r["cac"], r["churn"]), ha="center", va="center", fontsize=8)
ax2.set_xlabel("CAC (₹)"); ax2.set_ylabel("Churn %")
ax2.set_title("CAC vs churn by channel", loc="left", fontsize=12, fontweight="bold")
ax2.spines[["top", "right"]].set_visible(False)

# Geographic bubble map (lat/lon)
ax3 = fig.add_axes([0.05, 0.06, 0.40, 0.35])
geo = df.groupby(["state", "lat", "lon"], as_index=False)["revenue"].sum()
sc = ax3.scatter(geo["lon"], geo["lat"], s=geo["revenue"] / geo["revenue"].max() * 1800, c=geo["revenue"],
                 cmap="YlOrRd", alpha=.8, edgecolor="#555")
for _, r in geo.iterrows():
    ax3.annotate(r["state"], (r["lon"], r["lat"]), ha="center", va="bottom", fontsize=7, xytext=(0, 12), textcoords="offset points")
ax3.set_xlim(67, 98); ax3.set_ylim(7, 33)
ax3.set_title("Revenue by state (geographic heatmap)", loc="left", fontsize=12, fontweight="bold")
ax3.set_xticks([]); ax3.set_yticks([])
fig.colorbar(sc, ax=ax3, fraction=.04, label="Revenue ₹")

# Revenue by state bar (drill-down view)
ax4 = fig.add_axes([0.56, 0.06, 0.40, 0.35])
b = geo.sort_values("revenue")
ax4.barh(b["state"], b["revenue"] / 1e7, color="#e07a1f")
ax4.set_title("Top states by revenue (₹ Cr)", loc="left", fontsize=12, fontweight="bold")
ax4.spines[["top", "right"]].set_visible(False)

fig.text(0.04, 0.02, "Layout: KPIs → trend & relationships → geography → state detail.  Interactive version: Streamlit app.",
         fontsize=9, color="#6b7280")

with PdfPages("Dashboard_Export.pdf") as pdf:
    pdf.savefig(fig)
fig.savefig("dashboard_preview.png", dpi=70)
print("ok", k)
