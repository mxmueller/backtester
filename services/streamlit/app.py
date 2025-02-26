import streamlit as st
import os
from api import APIClient
from config import Config
from tabs import market_overview, symbol_analysis, strategy_performance, pairs_analysis, strategy_comparison

st.set_page_config(
    page_title="Stock Trading Analysis",
    page_icon="📈",
    layout="wide"
)

if not os.path.exists("tabs"):
    os.makedirs("tabs")


def main():
    st.title("Stock Trading Analysis")

    api_client = APIClient()
    config = Config(api_client)

    with st.sidebar:
        st.header("Configuration")
        markets = api_client.get_markets()
        selected_market = st.selectbox("Select Market", markets["markets"])

        strategies = api_client.get_market_strategies(selected_market)
        if strategies and "strategies" in strategies and len(strategies["strategies"]) > 0:
            strategy_options = [s["version"] for s in strategies["strategies"]]
            selected_strategy = st.selectbox("Select Strategy", strategy_options)
        else:
            selected_strategy = None
            st.error("No strategies available for selected market")

        st.subheader("Trading Parameters")
        initial_capital = st.number_input("Initial Capital", min_value=1000.0, value=100000.0, step=1000.0)
        position_size_percent = st.slider("Position Size (%)", min_value=0.1, max_value=10.0, value=1.0, step=0.1) / 100
        fixed_commission = st.number_input("Fixed Commission", min_value=0.0, value=1.0, step=0.1)
        variable_fee = st.number_input("Variable Fee (%)", min_value=0.0, value=0.018, step=0.001, format="%.3f") / 100
        bid_ask_spread = st.number_input("Bid-Ask Spread (%)", min_value=0.0, value=0.1, step=0.01) / 100
        risk_free_rate = st.number_input("Risk-Free Rate (%)", min_value=0.0, value=0.0, step=0.1) / 100

        trading_params = {
            "initial_capital": initial_capital,
            "position_size_percent": position_size_percent,
            "fixed_commission": fixed_commission,
            "variable_fee": variable_fee,
            "bid_ask_spread": bid_ask_spread,
            "risk_free_rate": risk_free_rate
        }

        config.set_market(selected_market)
        config.set_strategy(selected_strategy)
        config.set_trading_params(trading_params)

    if selected_market and selected_strategy:
        tabs = st.tabs(
            ["Market Overview", "Symbol Analysis", "Strategy Performance", "Pairs Analysis", "Strategy Comparison"])

        with tabs[0]:
            market_overview.render(api_client, config)

        with tabs[1]:
            symbol_analysis.render(api_client, config)

        with tabs[2]:
            strategy_performance.render(api_client, config)

        with tabs[3]:
            pairs_analysis.render(api_client, config)

        with tabs[4]:
            strategy_comparison.render(api_client, config)
    else:
        st.info("Please select a market and strategy to continue")


if __name__ == "__main__":
    main()