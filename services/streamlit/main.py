import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
from api import APIClient

st.set_page_config(layout="wide")


def create_timeseries_chart(data):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                        vertical_spacing=0.05,
                        row_heights=[0.4, 0.2, 0.2, 0.2],
                        subplot_titles=(
                        "Portfolio Performance", "Capital Allocation", "Active Positions", "Daily PnL & Costs"))

    dates = list(data.keys())

    # Performance with and without costs
    fig.add_trace(
        go.Scatter(x=dates, y=[d['performance_pct'] * 100 for d in data.values()],
                   name="Net Performance", line=dict(color='blue')), row=1, col=1)
    fig.add_trace(
        go.Scatter(x=dates, y=[(d['cumulative_pnl'] / d['total_capital']) * 100 for d in data.values()],
                   name="Gross Performance", line=dict(color='lightblue', dash='dash')), row=1, col=1)

    # Capital allocation
    fig.add_trace(
        go.Scatter(x=dates, y=[d['invested_capital'] for d in data.values()],
                   name="Invested", line=dict(color='orange')), row=2, col=1)
    fig.add_trace(
        go.Scatter(x=dates, y=[d['available_capital'] for d in data.values()],
                   name="Available", line=dict(color='green')), row=2, col=1)

    # Active positions
    fig.add_trace(
        go.Bar(x=dates, y=[d['active_positions'] for d in data.values()],
               name="Active Positions", marker_color='purple'), row=3, col=1)

    # Daily PnL and costs
    fig.add_trace(
        go.Bar(x=dates, y=[d['daily_pnl'] for d in data.values()],
               name="Daily PnL"), row=4, col=1)
    fig.add_trace(
        go.Scatter(x=dates, y=[d['daily_costs'] for d in data.values()],
                   name="Daily Costs", line=dict(color='red')), row=4, col=1)

    fig.update_layout(height=1000, showlegend=True)

    # Add percentage symbols to first y-axis
    fig.update_yaxes(ticksuffix="%", row=1, col=1)

    return fig


async def main():
    st.title("Trading Performance Analysis")

    trading_params = {
        "initial_capital": st.sidebar.number_input("Initial Capital", 10000, 1000000, 100000, step=10000),
        "position_size_percent": st.sidebar.slider("Position Size %", 0.1, 5.0, 1.0, 0.1) / 100,
        "fixed_commission": st.sidebar.number_input("Fixed Commission", 0.0, 10.0, 1.0, 0.1),
        "variable_fee": st.sidebar.number_input("Variable Fee %", 0.0, 1.0, 0.018, 0.001) / 100,
        "bid_ask_spread": st.sidebar.number_input("Bid-Ask Spread %", 0.0, 1.0, 0.1, 0.01) / 100,
        "risk_free_rate": st.sidebar.number_input("Risk Free Rate %", 0.0, 10.0, 0.0, 0.1) / 100
    }

    async with APIClient() as client:
        markets = await client.get_markets()
        market = st.selectbox("Select Market", markets)

        timeseries = await client.get_performance_timeseries(market, trading_params)

        if timeseries:
            last_data = list(timeseries.values())[-1]
            cols = st.columns(4)

            net_perf = last_data['performance_pct'] * 100
            gross_perf = (last_data['cumulative_pnl'] / last_data['total_capital']) * 100
            cost_impact = gross_perf - net_perf

            cols[0].metric("Net Performance", f"{net_perf:.1f}%")
            cols[1].metric("Gross Performance", f"{gross_perf:.1f}%")
            cols[2].metric("Cost Impact", f"{cost_impact:.1f}%")
            cols[3].metric("Active Positions", last_data['active_positions'])

            fig = create_timeseries_chart(timeseries)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Raw Timeseries Data"):
                st.json(timeseries)


if __name__ == "__main__":
    asyncio.run(main())