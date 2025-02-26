import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from api import APIClient
from config import Config


def render(api_client: APIClient, config: Config):
    st.header("Strategy Performance")

    market = config.get_market()
    strategy = config.get_strategy()
    trading_params = config.get_trading_params()

    if not market or not strategy:
        st.warning("Market and strategy must be selected")
        return

    # Get performance data
    performance_data = api_client.get_trades_performance(market, strategy, trading_params)
    timeseries_data = api_client.get_trades_performance_timeseries(market, strategy, trading_params)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Performance Over Time")

        if timeseries_data and 'timeseries' in timeseries_data:
            ts_df = pd.DataFrame.from_dict(timeseries_data['timeseries'], orient='index')

            if not ts_df.empty:
                ts_df.index = pd.to_datetime(ts_df.index)
                ts_df = ts_df.sort_index()

                # Portfolio equity curve
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=ts_df.index,
                    y=ts_df['total_capital'],
                    mode='lines',
                    name='Total Capital'
                ))

                if 'initial_capital' in trading_params:
                    fig.add_hline(
                        y=trading_params['initial_capital'],
                        line_dash="dash",
                        line_color="red",
                        annotation_text="Initial Capital"
                    )

                fig.update_layout(
                    title="Portfolio Equity Curve",
                    xaxis_title="Date",
                    yaxis_title="Capital",
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)

                # Daily P&L
                fig_pnl = go.Figure()

                fig_pnl.add_trace(go.Bar(
                    x=ts_df.index,
                    y=ts_df['daily_pnl'],
                    name='Daily P&L',
                    marker_color=ts_df['daily_pnl'].apply(lambda x: 'green' if x > 0 else 'red')
                ))

                fig_pnl.update_layout(
                    title="Daily Profit/Loss",
                    xaxis_title="Date",
                    yaxis_title="P&L",
                    height=250
                )
                st.plotly_chart(fig_pnl, use_container_width=True)

                # Cumulative metrics
                col_a, col_b, col_c = st.columns(3)

                with col_a:
                    if 'cumulative_pnl' in ts_df.columns:
                        final_pnl = ts_df['cumulative_pnl'].iloc[-1]
                        st.metric("Cumulative P&L", f"${final_pnl:.2f}")

                with col_b:
                    if 'net_performance' in ts_df.columns:
                        final_net = ts_df['net_performance'].iloc[-1]
                        st.metric("Net P&L (after costs)", f"${final_net:.2f}")

                with col_c:
                    if 'performance_pct' in ts_df.columns:
                        final_pct = ts_df['performance_pct'].iloc[-1] * 100
                        st.metric("Total Return", f"{final_pct:.2f}%")

                # Active positions over time
                if 'active_positions' in ts_df.columns:
                    fig_pos = px.line(
                        ts_df,
                        x=ts_df.index,
                        y='active_positions',
                        title="Active Positions Over Time"
                    )
                    fig_pos.update_layout(height=250)
                    st.plotly_chart(fig_pos, use_container_width=True)
            else:
                st.warning("No timeseries data available")
        else:
            st.warning("Failed to fetch performance timeseries data")

    with col2:
        st.subheader("Performance Metrics")

        if performance_data and 'performance' in performance_data:
            perf = performance_data['performance']

            # Main metrics
            metrics_cols = st.columns(2)

            with metrics_cols[0]:
                st.metric("Total Trades", perf.get('total_trades', 0))
                if 'portfolio' in perf:
                    init_cap = perf['portfolio'].get('initial_capital', 0)
                    final_cap = perf['portfolio'].get('final_capital', 0)
                    pct_return = (final_cap - init_cap) / init_cap * 100 if init_cap else 0
                    st.metric(
                        "Final Capital",
                        f"${final_cap:.2f}",
                        f"{pct_return:.2f}%"
                    )
                if 'net_performance' in perf:
                    st.metric("Win Rate", f"{perf['net_performance'].get('win_rate', 0):.2%}")

            with metrics_cols[1]:
                st.metric("Profitable Days", f"{perf.get('profitable_days', 0)} / {perf.get('total_days', 0)}")
                if 'sharpe_ratio' in perf and perf['sharpe_ratio'] is not None:
                    st.metric("Sharpe Ratio", f"{perf['sharpe_ratio']:.2f}")
                if 'max_drawdown' in perf:
                    st.metric("Max Drawdown", f"{perf['max_drawdown'] * 100:.2f}%")

            # Detailed metrics tabs
            metrics_tabs = st.tabs(["Performance", "Costs", "Portfolio"])

            with metrics_tabs[0]:
                if 'net_performance' in perf:
                    net_perf = perf['net_performance']
                    perf_df = pd.DataFrame({
                        'Metric': [
                            'Total Performance',
                            'Avg Performance',
                            'Max Gain',
                            'Max Loss',
                            'Profitable Trades',
                            'Total Trades'
                        ],
                        'Value': [
                            f"{net_perf.get('total_performance', 0):.2%}",
                            f"{net_perf.get('avg_performance', 0):.2%}",
                            f"{net_perf.get('max_gain', 0):.2%}",
                            f"{net_perf.get('max_loss', 0):.2%}",
                            net_perf.get('profitable_trades', 0),
                            net_perf.get('total_trades', 0)
                        ]
                    })
                    st.dataframe(perf_df, hide_index=True, use_container_width=True)

            with metrics_tabs[1]:
                if 'costs' in perf:
                    costs = perf['costs']
                    st.metric("Total Costs", f"${costs.get('total_costs', 0):.2f}")
                    st.metric("Avg Cost/Trade", f"${costs.get('avg_cost_per_trade', 0):.2f}")

                    if 'breakdown' in costs:
                        bd = costs['breakdown']
                        if 'entry' in bd and 'exit' in bd:
                            cost_df = pd.DataFrame({
                                'Type': ['Commission', 'Variable Fee', 'Spread', 'Total'],
                                'Entry': [
                                    f"${bd['entry'].get('commission', 0):.2f}",
                                    f"${bd['entry'].get('variable', 0):.2f}",
                                    f"${bd['entry'].get('spread', 0):.2f}",
                                    f"${bd['entry'].get('total', 0):.2f}"
                                ],
                                'Exit': [
                                    f"${bd['exit'].get('commission', 0):.2f}",
                                    f"${bd['exit'].get('variable', 0):.2f}",
                                    f"${bd['exit'].get('spread', 0):.2f}",
                                    f"${bd['exit'].get('total', 0):.2f}"
                                ]
                            })
                            st.dataframe(cost_df, hide_index=True, use_container_width=True)

            with metrics_tabs[2]:
                if 'portfolio' in perf:
                    port = perf['portfolio']
                    port_df = pd.DataFrame({
                        'Metric': [
                            'Initial Capital',
                            'Final Capital',
                            'Max Capital',
                            'Min Capital',
                            'Current Invested',
                            'Current Available'
                        ],
                        'Value': [
                            f"${port.get('initial_capital', 0):.2f}",
                            f"${port.get('final_capital', 0):.2f}",
                            f"${port.get('max_capital', 0):.2f}",
                            f"${port.get('min_capital', 0):.2f}",
                            f"${port.get('current_invested', 0):.2f}",
                            f"${port.get('current_available', 0):.2f}"
                        ]
                    })
                    st.dataframe(port_df, hide_index=True, use_container_width=True)
        else:
            st.warning("Failed to fetch performance data")