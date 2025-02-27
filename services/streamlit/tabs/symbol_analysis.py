import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from api import APIClient
from config import Config

def render(api_client: APIClient, config: Config):
    st.header("Symbol Analysis")

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

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Price History")

        symbol_data = api_client.get_timeseries(market, selected_symbol)

        if symbol_data:
            
            df = pd.DataFrame([
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

            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
 
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['close'],
                    mode='lines',
                    name='Close Price'
                ))

                fig.update_layout(
                    title=f"{selected_symbol} Price History",
                    xaxis_title="Date",
                    yaxis_title="Price",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True, key="price_history_chart")
          
                if len(df) > 0:
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Current Price", f"${df['close'].iloc[-1]:.2f}")

                    price_change = df['close'].iloc[-1] - df['close'].iloc[0]
                    price_change_pct = (price_change / df['close'].iloc[0]) * 100
                    col_b.metric("Price Change", f"${price_change:.2f}", f"{price_change_pct:.2f}%")

                    col_c.metric("Volatility", f"{df['close'].std():.2f}")
            else:
                st.warning("No price data available for this symbol")
        else:
            st.warning("Failed to fetch price data")

    with col2:
        st.subheader("Symbol Trades")
   
        symbol_trades = api_client.get_symbol_trades(market, selected_symbol, strategy)

        if symbol_trades:
            
            trades_df = pd.DataFrame(symbol_trades)

            if not trades_df.empty:
                
                for date_col in ['entry_date', 'exit_date']:
                    if date_col in trades_df.columns:
                        trades_df[date_col] = pd.to_datetime(trades_df[date_col])

                
                total_trades = len(trades_df)
                profitable_trades = len(trades_df[trades_df['performance'] > 0])
                win_rate = profitable_trades / total_trades if total_trades > 0 else 0

                st.metric("Total Trades", total_trades)
                st.metric("Win Rate", f"{win_rate:.2%}")

                
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
          
                st.subheader("Recent Trades")
                display_cols = ['entry_date', 'exit_date', 'position_type', 'entry_price',
                                'exit_price', 'performance', 'exit_type']
                display_df = trades_df[display_cols].copy() if all(
                    col in trades_df.columns for col in display_cols) else trades_df

                
                if 'performance' in display_df.columns:
                    display_df['performance'] = display_df['performance'].apply(lambda x: f"{x:.2%}")

                st.dataframe(
                    display_df.sort_values('entry_date', ascending=False).head(10),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No trades for this symbol")
        else:
            st.info("No trades data available")

    
    if 'symbol_trades' in locals() and symbol_trades:
        st.subheader("Trade Performance Over Time")

        trades_df = pd.DataFrame(symbol_trades)
        if not trades_df.empty and 'entry_date' in trades_df.columns and 'performance' in trades_df.columns:
            trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date'])
            trades_df = trades_df.sort_values('entry_date')

            fig = px.scatter(
                trades_df,
                x='entry_date',
                y='performance',
                color='position_type' if 'position_type' in trades_df.columns else None,
                title=f"Trade Performance for {selected_symbol}",
                color_discrete_map={'long': 'blue', 'short': 'red'}
            )

            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True, key="trade_performance_chart")

            
            if len(trades_df) > 0:
                trades_df['cum_performance'] = trades_df['performance'].cumsum()

                fig_cum = px.line(
                    trades_df,
                    x='entry_date',
                    y='cum_performance',
                    title=f"Cumulative Performance for {selected_symbol}",
                )
                fig_cum.update_layout(height=300)
                st.plotly_chart(fig_cum, use_container_width=True, key="cumulative_performance_chart")
        else:
            st.info("Insufficient data to plot performance over time")