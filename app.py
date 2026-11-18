import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_gen import make_data, kpis, fmt_inr, CATEGORIES, CHANNELS

st.set_page_config(page_title="Executive KPI Dashboard", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.5rem;}
      .kpi {background:#fff;border:1px solid #e6e6ea;border-radius:12px;padding:14px 18px;}
      .kpi .l {font-size:.75rem;letter-spacing:.06em;text-transform:uppercase;color:#6b7280;}
      .kpi .v {font-size:1.8rem;font-weight:700;color:#111827;line-height:1.2;}
      .up {color:#16a34a;font-size:.85rem;} .down {color:#dc2626;font-size:.85rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load() -> pd.DataFrame:
    return make_data()


df = load()

# ---------------- Slicers ----------------
st.sidebar.header("Filters")
yrs = sorted(df["month"].dt.year.unique())
year = st.sidebar.multiselect("Year", yrs, default=yrs)
region = st.sidebar.multiselect("Region", sorted(df["region"].unique()), default=sorted(df["region"].unique()))
cat = st.sidebar.multiselect("Category", CATEGORIES, default=CATEGORIES)
ch = st.sidebar.multiselect("Channel", CHANNELS, default=CHANNELS)
grain = st.sidebar.radio("Time granularity (drill-down)", ["Year", "Quarter", "Month"], index=2)

f = df[
    df["month"].dt.year.isin(year) & df["region"].isin(region)
    & df["category"].isin(cat) & df["channel"].isin(ch)
]
if f.empty:
    st.warning("No data for the selected filters.")
    st.stop()

# ---------------- Header ----------------
st.title("Executive KPI Dashboard")
st.caption("Revenue • Customer Acquisition Cost • Churn Rate • Average Order Value  |  synthetic e-commerce data, India")

# ---------------- KPI cards (with period-over-period delta) ----------------
cur = kpis(f)
last_year = f["month"].dt.year.max()
cur_y, prev_y = f[f["month"].dt.year == last_year], f[f["month"].dt.year == last_year - 1]


def delta(key, invert=False):
    if prev_y.empty:
        return ""
    a, b = kpis(cur_y)[key], kpis(prev_y)[key]
    if b == 0:
        return ""
    pct = (a - b) / b * 100
    good = (pct < 0) if invert else (pct > 0)
    arrow = "▲" if pct > 0 else "▼"
    return f'<span class="{"up" if good else "down"}">{arrow} {abs(pct):.1f}% vs {last_year-1}</span>'


c1, c2, c3, c4 = st.columns(4)
for col, label, val, d in [
    (c1, "Revenue", fmt_inr(cur["revenue"]), delta("revenue")),
    (c2, "Customer Acquisition Cost", f"₹{cur['cac']:,.0f}", delta("cac", invert=True)),
    (c3, "Churn Rate", f"{cur['churn']:.2f}%", delta("churn", invert=True)),
    (c4, "Average Order Value", f"₹{cur['aov']:,.0f}", delta("aov")),
]:
    col.markdown(f'<div class="kpi"><div class="l">{label}</div><div class="v">{val}</div>{d}</div>', unsafe_allow_html=True)

st.write("")

# ---------------- Trend (area) with drill-down ----------------
g = f.copy()
if grain == "Year":
    g["period"] = g["month"].dt.year.astype(str)
elif grain == "Quarter":
    g["period"] = g["month"].dt.to_period("Q").astype(str)
else:
    g["period"] = g["month"].dt.to_period("M").dt.to_timestamp()

left, right = st.columns([3, 2])
with left:
    st.subheader("Revenue trend")
    trend = g.groupby(["period", "category"], as_index=False)["revenue"].sum()
    fig = px.area(trend, x="period", y="revenue", color="category",
                  color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0), legend_title_text="",
                      yaxis_title="Revenue (₹)", xaxis_title=None, legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("CAC vs churn by channel")
    ch_df = f.groupby("channel").apply(
        lambda d: pd.Series({"CAC": d["acq_spend"].sum() / d["new_customers"].sum(),
                             "Churn %": d["churned"].sum() / d["start_customers"].sum() * 100,
                             "Revenue": d["revenue"].sum()}), include_groups=False).reset_index()
    fig2 = px.scatter(ch_df, x="CAC", y="Churn %", size="Revenue", color="channel", size_max=45,
                      color_discrete_sequence=px.colors.qualitative.Set2)
    fig2.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0), showlegend=True,
                       legend=dict(orientation="h", y=-0.2), legend_title_text="")
    st.plotly_chart(fig2, width="stretch")

# ---------------- Geographic heatmap ----------------
st.subheader("Geographic heatmap — revenue by state")
geo = f.groupby(["state", "lat", "lon"], as_index=False).agg(revenue=("revenue", "sum"), orders=("orders", "sum"))
geo["aov"] = geo["revenue"] / geo["orders"]
fig3 = px.scatter_geo(geo, lat="lat", lon="lon", size="revenue", color="revenue", hover_name="state",
                      hover_data={"lat": False, "lon": False, "revenue": ":,.0f", "aov": ":,.0f"},
                      color_continuous_scale="YlOrRd", size_max=50, scope="asia")
fig3.update_geos(lataxis_range=[6, 36], lonaxis_range=[67, 98], showcountries=True,
                 countrycolor="#bbb", showland=True, landcolor="#f5f5f0", showocean=True, oceancolor="#eef4fa")
fig3.update_layout(height=460, margin=dict(l=0, r=0, t=0, b=0), coloraxis_colorbar=dict(title="Revenue ₹"))
st.plotly_chart(fig3, width="stretch")

# ---------------- Drill-down: region -> state -> category ----------------
st.subheader("Drill-down: Region → State → Category")
sun = f.groupby(["region", "state", "category"], as_index=False)["revenue"].sum()
fig4 = px.sunburst(sun, path=["region", "state", "category"], values="revenue",
                   color_discrete_sequence=px.colors.qualitative.Set2)
fig4.update_layout(height=480, margin=dict(l=0, r=0, t=0, b=0))
d1, d2 = st.columns([2, 3])
with d1:
    st.plotly_chart(fig4, width="stretch")
with d2:
    sel_state = st.selectbox("Drill into a state", sorted(f["state"].unique()))
    s = f[f["state"] == sel_state]
    k = kpis(s)
    st.write(f"**{sel_state}** — Revenue {fmt_inr(k['revenue'])} · CAC ₹{k['cac']:,.0f} · "
             f"Churn {k['churn']:.2f}% · AOV ₹{k['aov']:,.0f}")
    sm = s.groupby(s["month"].dt.to_period("M").dt.to_timestamp())["revenue"].sum().reset_index()
    fig5 = go.Figure(go.Scatter(x=sm["month"], y=sm["revenue"], mode="lines", fill="tozeroy",
                                line=dict(color="#e07a1f")))
    fig5.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Revenue (₹)")
    st.plotly_chart(fig5, width="stretch")
    st.dataframe(s.groupby("category")[["revenue", "orders"]].sum().sort_values("revenue", ascending=False)
                 .style.format({"revenue": "₹{:,.0f}", "orders": "{:,.0f}"}), width="stretch")

st.caption("Layout: KPIs at the top (scan first) → trend + relationship charts → geography → drill-down detail.")
