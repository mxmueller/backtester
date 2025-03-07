import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from api import APIClient
from config import Config
from plotly.subplots import make_subplots


def render(api_client: APIClient, config: Config):
    st.header("Symbol Analysis")

    st.markdown(
        "This analysis shows how the trading strategy performs compared to a simple buy and hold approach. The top chart displays price history alongside both return types, while the bottom chart shows individual trade performance.")

    market = config.get_market()
    strategy = config.get_strategy()
    trading_params = config.get_trading_params()

    if not market or not strategy:
        st.warning("Market and strategy must be selected")
        return

    symbols = config.get_symbols()

    if not symbols:
        st.warning("No symbols available for this market")
        return

    selected_symbol = st.selectbox(
        "Select Symbol",
        symbols,
        key="symbol_selector"
    )

    if not selected_symbol:
        st.info("Please select a symbol")
        return

    symbol_data = api_client.get_timeseries(market, selected_symbol)
    symbol_trades = api_client.get_symbol_trades(market, selected_symbol, strategy)

    # Default values for global variables
    y2_min = -0.2
    y2_max = 0.2

    # Process data for visualization
    price_df = pd.DataFrame()
    trades_df = pd.DataFrame()

    # Process price data
    if symbol_data:
        price_df = pd.DataFrame([
            {
                'date': date,
                'close': data['close'],
                'open': data.get('open', None),
                'high': data.get('high', None),
                'low': data.get('low', None),
                'volume': data.get('volume', None)
            }
            for date, data in symbol_data.items()
        ])

        if not price_df.empty:
            price_df['date'] = pd.to_datetime(price_df['date'])
            price_df = price_df.sort_values('date')

    # Process trade data
    if symbol_trades:
        trades_df = pd.DataFrame(symbol_trades)

        if not trades_df.empty and 'entry_date' in trades_df.columns and 'performance' in trades_df.columns:
            trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date'])
            if 'exit_date' in trades_df.columns:
                trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date'])
            trades_df = trades_df.sort_values('entry_date')
            trades_df['cum_performance'] = trades_df['performance'].cumsum()

    # Create combined chart only if we have both price and trade data
    if not price_df.empty and not trades_df.empty:
        # Filter price data to trading period
        first_trade_date = trades_df['entry_date'].min()
        last_trade_date = trades_df['entry_date'].max()

        filtered_price = price_df[(price_df['date'] >= first_trade_date) & (price_df['date'] <= last_trade_date)]

        if not filtered_price.empty:
            initial_price = filtered_price['close'].iloc[0]
            filtered_price['buy_hold_return'] = filtered_price['close'] / initial_price - 1

            # Calculate dynamic y-axis range for returns
            max_return = max(filtered_price['buy_hold_return'].max(), trades_df['cum_performance'].max())
            min_return = min(filtered_price['buy_hold_return'].min(), trades_df['cum_performance'].min())

            y2_max = max(0.2, max_return * 1.2)
            y2_min = min(-0.2, min_return * 1.2)

            # Create subplot with 2 rows, one for price/returns and one for individual trades
            fig = make_subplots(
                rows=2,
                cols=1,
                row_heights=[0.7, 0.3],
                vertical_spacing=0.08,
                specs=[
                    [{"secondary_y": True}],
                    [{"secondary_y": False}]
                ],
                shared_xaxes=True
            )

            # Add traces to first subplot (price and returns)
            fig.add_trace(
                go.Scatter(
                    x=filtered_price['date'],
                    y=filtered_price['close'],
                    mode='lines',
                    name='Price History',
                    line=dict(color='goldenrod')
                ),
                row=1, col=1, secondary_y=False
            )

            fig.add_trace(
                go.Scatter(
                    x=filtered_price['date'],
                    y=filtered_price['buy_hold_return'],
                    mode='lines',
                    name='Buy & Hold Return',
                    line=dict(color='green')
                ),
                row=1, col=1, secondary_y=True
            )

            fig.add_trace(
                go.Scatter(
                    x=trades_df['entry_date'],
                    y=trades_df['cum_performance'],
                    mode='lines',
                    name='Trading Strategy Return',
                    line=dict(color='magenta')
                ),
                row=1, col=1, secondary_y=True
            )

            # Add individual trades to second subplot
            fig.add_trace(
                go.Scatter(
                    x=trades_df[trades_df['performance'] > 0]['entry_date'],
                    y=trades_df[trades_df['performance'] > 0]['performance'],
                    mode='markers',
                    name='Profitable Trades',
                    marker=dict(
                        color='blue',
                        size=10,
                        symbol='circle'
                    ),
                    hovertemplate='<b>Date</b>: %{x}<br><b>Return</b>: %{y:.2%}<extra></extra>',
                    customdata=trades_df[trades_df['performance'] > 0][
                        'position_type'] if 'position_type' in trades_df.columns else None,
                    visible="legendonly" if all(trades_df['performance'] <= 0) else True
                ),
                row=2, col=1
            )

            # Add losing trades with different marker
            fig.add_trace(
                go.Scatter(
                    x=trades_df[trades_df['performance'] <= 0]['entry_date'],
                    y=trades_df[trades_df['performance'] <= 0]['performance'],
                    mode='markers',
                    name='Losing Trades',
                    marker=dict(
                        color='red',
                        size=10,
                        symbol='circle'
                    ),
                    hovertemplate='<b>Date</b>: %{x}<br><b>Return</b>: %{y:.2%}<extra></extra>',
                    customdata=trades_df[trades_df['performance'] <= 0][
                        'position_type'] if 'position_type' in trades_df.columns else None,
                    visible="legendonly" if all(trades_df['performance'] > 0) else True
                ),
                row=2, col=1
            )

            # Add zero line to second subplot
            fig.add_shape(
                type="line",
                x0=trades_df['entry_date'].min(),
                x1=trades_df['entry_date'].max(),
                y0=0,
                y1=0,
                line=dict(color="gray", width=1, dash="dash"),
                row=2, col=1
            )

            # Update layout
            fig.update_layout(
                title=f"{selected_symbol} Trading Period Analysis",
                height=600,
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=60, r=60, t=60, b=50)
            )

            # Update y-axes
            fig.update_yaxes(title="Price ($)", secondary_y=False, row=1, col=1)
            fig.update_yaxes(
                title="Return (%)",
                secondary_y=True,
                row=1,
                col=1,
                tickformat=".1%",
                range=[y2_min, y2_max]
            )
            fig.update_yaxes(
                title="Trade Return (%)",
                tickformat=".1%",
                row=2,
                col=1
            )

            # Update x-axes
            fig.update_xaxes(title="", row=1, col=1)
            fig.update_xaxes(title="Date", row=2, col=1)

            # Display the chart
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No price data available for the trading period")
    else:
        st.warning("Insufficient data to create analysis charts")

    # After charts, add the full-width trades table
    if symbol_trades and not trades_df.empty:
        st.subheader("All Trades")

        # Prepare the dataframe for display
        display_cols = ['entry_date', 'exit_date', 'position_type', 'entry_price',
                        'exit_price', 'performance', 'exit_type']

        display_df = trades_df[display_cols].copy() if all(
            col in trades_df.columns for col in display_cols) else trades_df

        if 'performance' in display_df.columns:
            display_df['performance'] = display_df['performance'].apply(lambda x: f"{x:.2%}")

        # Show the full table with sorting enabled
        st.dataframe(
            display_df.sort_values('entry_date', ascending=False),
            use_container_width=True,
            hide_index=True
        )

    # Create two-column layout for Symbol Trades info
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Symbol Trades")

        if symbol_trades and not trades_df.empty:
            total_trades = len(trades_df)
            profitable_trades = len(trades_df[trades_df['performance'] > 0])
            win_rate = profitable_trades / total_trades if total_trades > 0 else 0

            st.metric("Total Trades", total_trades)
            st.metric("Win Rate", f"{win_rate:.2%}")
        else:
            st.info("No trades data available")

    with col2:
        if symbol_trades and not trades_df.empty:
            symbol_performance = api_client.get_symbol_performance(
                market,
                selected_symbol,
                strategy,
                trading_params=trading_params
            )

            if symbol_performance and 'net_performance' in symbol_performance:
                net_perf = symbol_performance['net_performance']

                metrics_df = pd.DataFrame({
                    'Metric': [
                        'Total Performance',
                        'Avg Performance',
                        'Max Gain',
                        'Max Loss'
                    ],
                    'Value': [
                        f"{net_perf.get('total_performance', 0):.2%}",
                        f"{net_perf.get('avg_performance', 0):.2%}",
                        f"{net_perf.get('max_gain', 0):.2%}",
                        f"{net_perf.get('max_loss', 0):.2%}"
                    ]
                })
                st.dataframe(metrics_df, hide_index=True, use_container_width=True)