# trading performance & risk monitoring platform
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from openpyxl import load_workbook
import pandas as pd

# -----------------------------
# App Config
# -----------------------------
st.set_page_config(
    page_title="Trading Performance Dashboard",
    layout="wide"
)

# -----------------------------
# Data Loading
# -----------------------------
@st.cache_data
def load_data(file):
    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)
    df.columns = df.columns.str.strip()
    return df

# -----------------------------
# Metrics Engine
# -----------------------------
def compute_metrics(df):
    pnl = df["Master Gain"]

    metrics = {
        "total_pnl": pnl.sum(),
        "avg_pnl": pnl.mean(),
        "win_rate": (pnl > 0).mean(),
        "num_tickers": df["Ticker"].nunique(),
        "top_contribution": pnl.max() / pnl.sum() if pnl.sum() != 0 else 0
    }
    return metrics

# -----------------------------
# Overview View
# -----------------------------
def overview_view(df):
    metrics = compute_metrics(df)
    wl = win_loss_metrics(df)

    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    col1.metric("Total PnL", f"${metrics['total_pnl']:,.2f}")
    col2.metric("Avg PnL / Ticker", f"${metrics['avg_pnl']:,.2f}")
    col3.metric("Win Rate", f"{metrics['win_rate']*100:.1f}%")
    col4.metric("Tickers Traded", metrics["num_tickers"])
    col5.metric("Top Ticker Contribution", f"{metrics['top_contribution']*100:.1f}%")
    col6.metric("Avg Winning Trade", f"${wl['avg_win']:,.2f}")
    col7.metric("Avg Losing Trade", f"${wl['avg_loss']:,.2f}")
    col8.metric("Profit Factor", f"{wl['profit_factor']:.2f}")
    
    st.info(generate_insight(df))

    st.divider()

    sorted_df = df.sort_values("Master Gain", ascending=False)

    fig = px.bar(
        sorted_df,
        x="Ticker",
        y="Master Gain",
        title="PnL by Ticker",
        color="Master Gain",
        color_continuous_scale="RdYlGn"
    )

    st.plotly_chart(fig, width='stretch')

# -----------------------------
# Ticker Deep Dive
# -----------------------------
def ticker_view(df):
    ticker = st.selectbox("Select Ticker", df["Ticker"].unique())
    row = df[df["Ticker"] == ticker].iloc[0]

    st.subheader(f"📊 {ticker} Performance")

    col1, col2, col3 = st.columns(3)
    col1.metric("PnL", f"${row['Master Gain']:,.2f}")
    col2.metric("Portfolio Contribution", f"{row['Master Gain']/df['Master Gain'].sum()*100:.2f}%")
    col3.metric("Rank",
        df["Master Gain"].rank(ascending=False).loc[row.name]
    )

    comparison = df.sort_values("Master Gain", ascending=False).head(10)

    fig = px.bar(
        comparison,
        x="Ticker",
        y="Master Gain",
        title="Top 10 Tickers by PnL"
    )
    st.plotly_chart(fig, width='stretch')

# -----------------------------
# Risk & Concentration View
# -----------------------------
def risk_view(df):
    st.subheader("⚠️ Concentration & Risk")

    # Absolute contribution
    risk_df = df.copy()
    risk_df["Abs Gain"] = risk_df["Master Gain"].abs()

    total_abs = risk_df["Abs Gain"].sum()
    risk_df["Contribution %"] = risk_df["Abs Gain"] / total_abs
    risk_df = risk_df.sort_values("Contribution %", ascending=False)
    risk_df["Cumulative %"] = risk_df["Contribution %"].cumsum()

    fig = px.line(
        risk_df,
        x=range(1, len(risk_df) + 1),
        y="Cumulative %",
        markers=True,
        title="Cumulative Absolute PnL Contribution",
        labels={"x": "Top N Tickers", "Cumulative %": "Cumulative % of Total Risk"}
    )

    fig.add_hline(y=0.5, line_dash="dash", annotation_text="50% Threshold")
    fig.add_hline(y=0.75, line_dash="dash", annotation_text="75% Threshold")

    st.plotly_chart(fig, width='stretch')

    top_3 = risk_df.head(3)["Contribution %"].sum()

    if top_3 > 0.5:
        st.error(f"⚠️ High concentration: Top 3 tickers drive {top_3*100:.1f}% of total portfolio risk")
    else:
        st.success(f"✅ Diversified: Top 3 tickers drive {top_3*100:.1f}% of total portfolio risk")
        
def win_loss_metrics(df):
    wins = df[df["Master Gain"] > 0]["Master Gain"]
    losses = df[df["Master Gain"] < 0]["Master Gain"]

    return {
        "avg_win": wins.mean() if len(wins) else 0,
        "avg_loss": losses.mean() if len(losses) else 0,
        "profit_factor": wins.sum() / abs(losses.sum()) if len(losses) else np.inf
    }
    
def generate_insight(df):
    total_pnl = df["Master Gain"].sum()

    top = df.sort_values("Master Gain", ascending=False).head(1).iloc[0]
    worst = df.sort_values("Master Gain").head(1).iloc[0]

    insight = (
        f"**Portfolio PnL:** ${total_pnl:,.2f}\n\n"
        f"- Top performer: **{top['Ticker']}** (+${top['Master Gain']:,.2f})\n"
        f"- Largest drag: **{worst['Ticker']}** (-${abs(worst['Master Gain']):,.2f})"
    )
    return insight


# -----------------------------
# Data Audit View
# -----------------------------
def audit_view(df_main):
    st.subheader("🧪 Data Audit")

    st.caption(
        "Formula-derived values are read from Excel using cached results "
    )
    
    # df_audit = df_main[df_main["Ticker"].notna()].copy()

    # -------------------------
    # Missing Values Comparison
    # -------------------------
    st.markdown("### Missing Values")


    st.dataframe(df_main.isna().sum())

    # -------------------------
    # Descriptive Statistics
    # -------------------------
    st.markdown("### Descriptive Statistics")


    st.markdown("**Numeric Analytics**")
    st.dataframe(df_main[["Master Gain","Total Gain", "Calc Gain"]].describe())

    
def load_excel_with_formulas(file):
    wb = load_workbook(file, data_only=True)
    ws = wb.active

    data = ws.values
    columns = next(data)
    df = pd.DataFrame(data, columns=columns)

    return df

# -----------------------------
# Main App
# -----------------------------
def main():
    st.title("📈 Trading Performance Dashboard")

    uploaded_file = st.file_uploader(
        "Upload trading master file (CSV or Excel)",
        type=["csv", "xlsx"]
    )

    if uploaded_file:
        if uploaded_file.name.endswith(".xlsx"):
            df_main = pd.read_excel(uploaded_file)  # Python-native analytics
        else:
            df_main = pd.read_csv(uploaded_file)
        df_main = df_main[df_main["Ticker"].notna()].copy()
        view = st.sidebar.radio(
            "View",
            ["Overview", "Ticker Deep Dive", "Risk & Concentration", "Data Audit"]
        )

        if view == "Overview":
            overview_view(df_main)
        elif view == "Ticker Deep Dive":
            ticker_view(df_main)
        elif view == "Risk & Concentration":
            risk_view(df_main)
        elif view == "Data Audit":
            audit_view(df_main)

        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    else:
        st.info("📁 Upload a trading master file to begin")

if __name__ == "__main__":
    main()