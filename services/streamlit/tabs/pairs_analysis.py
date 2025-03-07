import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from api import APIClient
from config import Config


def render(api_client: APIClient, config: Config):
    st.header("Pairs Analysis")

    market = config.get_market()
    strategy = config.get_strategy()
    trading_params = config.get_trading_params()
    windows = config.get_windows()

    if not market or not strategy:
        st.warning("Market and strategy must be selected")
        return

    if not windows:
        st.warning("No trading windows available for this strategy")
        return

    
    selected_window = st.selectbox(
        "Select Trading Window",
        windows,
        format_func=lambda x: f"Window {x}",
        key="pairs_window_selector"
    )

    if not selected_window:
        st.info("Please select a trading window")
        return

    
    pairs_data = api_client.get_pairs_for_window(market, selected_window, strategy)

    if not pairs_data:
        st.warning(f"No pairs data available for window {selected_window}")
        return

    
    window_key = str(selected_window)
    window_data = pairs_data.get(window_key, {})

    if not window_data and selected_window in pairs_data:
        
        window_data = pairs_data.get(selected_window, {})

    if not window_data:
        st.warning(f"No pairs data found in response for window {selected_window}")
        st.write("API response structure:", pairs_data)
        return

    pairs_list = window_data.get('pairs', [])

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Pairs Overview")

        if pairs_list:
            
            pairs_df = pd.DataFrame([
                {
                    'Pair': f"{p['pair'][0]} - {p['pair'][1]}",
                    'Symbol 1': p['pair'][0],
                    'Symbol 2': p['pair'][1],
                    'Trades': p['trades']
                }
                for p in pairs_list
            ])
            
            total_pairs = window_data.get('total_pairs', 0)
            total_trades = window_data.get('total_trades', 0)

            col_a, col_b = st.columns(2)
            col_a.metric("Total Pairs", total_pairs)
            col_b.metric("Total Trades", total_trades)

            
            if not pairs_df.empty:
                pairs_df = pairs_df.sort_values('Trades', ascending=False)

                fig = px.bar(
                    pairs_df.head(20),  
                    x='Pair',
                    y='Trades',
                    title=f"Top 20 Pairs by Trade Count (Window {selected_window})",
                    color='Trades',
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(
                    xaxis_tickangle=-45,
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True, key="pairs_distribution_chart")

                
                st.dataframe(
                    pairs_df.sort_values('Trades', ascending=False),
                    use_container_width=True,
                    hide_index=True,
                    key="pairs_overview_table"
                )
        else:
            st.info("No pairs available for this window")

    with col2:
        st.subheader("Pair Analysis")

        if pairs_list:
            
            all_symbols = set()
            for p in pairs_list:
                all_symbols.update(p['pair'])

            
            symbol1 = st.selectbox(
                "Select First Symbol",
                sorted(list(all_symbols)),
                key="pairs_symbol1_selector"
            )

            
            valid_second_symbols = set()
            for p in pairs_list:
                if symbol1 in p['pair']:
                    valid_second_symbols.update(
                        [s for s in p['pair'] if s != symbol1]
                    )

            symbol2 = st.selectbox(
                "Select Second Symbol",
                sorted(list(valid_second_symbols)),
                key="pairs_symbol2_selector"
            )

            if symbol1 and symbol2:
                
                pair_performance = api_client.get_pair_performance(
                    market,
                    symbol1,
                    symbol2,
                    strategy,
                    window=selected_window,
                    trading_params=trading_params
                )

                if pair_performance:
                    
                    trade_count = 0
                    for p in pairs_list:
                        if symbol1 in p['pair'] and symbol2 in p['pair']:
                            trade_count = p['trades']
                            break

                    st.metric("Trades", trade_count)

                    
                    if 'net_performance' in pair_performance:
                        net_perf = pair_performance['net_performance']

                        metrics_df = pd.DataFrame({
                            'Metric': [
                                'Win Rate',
                                'Total Performance',
                                'Avg Performance',
                                'Max Gain',
                                'Max Loss'
                            ],
                            'Value': [
                                f"{net_perf['win_rate']:.2%}",
                                f"{net_perf['total_performance']:.2%}",
                                f"{net_perf['avg_performance']:.2%}",
                                f"{net_perf['max_gain']:.2%}",
                                f"{net_perf['max_loss']:.2%}"
                            ]
                        })
                        st.dataframe(
                            metrics_df,
                            use_container_width=True,
                            hide_index=True,
                            key="pairs_metrics_table"
                        )
          
                        if 'sharpe_ratio' in pair_performance and pair_performance['sharpe_ratio'] is not None:
                            st.metric("Sharpe Ratio", f"{pair_performance['sharpe_ratio']:.2f}")

                        
                        if 'costs' in pair_performance:
                            costs = pair_performance['costs']
                            st.metric("Total Costs", f"${costs.get('total_costs', 0):.2f}")
                            st.metric("Avg Cost/Trade", f"${costs.get('avg_cost_per_trade', 0):.2f}")
                    else:
                        st.warning("Performance data not available for this pair")
                else:
                    st.warning("Failed to fetch performance data for this pair")
            else:
                st.info("Select both symbols to analyze a pair")
        else:
            st.info("No pairs available for selection")

    
    if 'symbol1' in locals() and 'symbol2' in locals() and symbol1 and symbol2:
        #st.subheader("Pair Price Comparison")

        symbol1_data = api_client.get_timeseries(market, symbol1)
        symbol2_data = api_client.get_timeseries(market, symbol2)

        if symbol1_data and symbol2_data:
            
            df1 = pd.DataFrame([
                {
                    'date': date,
                    'price': data['close'],
                    'symbol': symbol1
                }
                for date, data in symbol1_data.items()
            ])

            df2 = pd.DataFrame([
                {
                    'date': date,
                    'price': data['close'],
                    'symbol': symbol2
                }
                for date, data in symbol2_data.items()
            ])

            combined_df = pd.concat([df1, df2])
            combined_df['date'] = pd.to_datetime(combined_df['date'])
            combined_df = combined_df.sort_values('date')

            
            pivot_df = combined_df.pivot(index='date', columns='symbol', values='price')
            start_date = pivot_df.index.min()

            for col in pivot_df.columns:
                start_val = pivot_df.loc[start_date, col]
                pivot_df[f"{col}_norm"] = pivot_df[col] / start_val * 100

            
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=pivot_df.index,
                y=pivot_df[f"{symbol1}_norm"],
                mode='lines',
                name=symbol1
            ))

            fig.add_trace(go.Scatter(
                x=pivot_df.index,
                y=pivot_df[f"{symbol2}_norm"],
                mode='lines',
                name=symbol2
            ))

            
            if len(pivot_df.columns) >= 4:  
                pivot_df['spread'] = pivot_df[f"{symbol1}_norm"] - pivot_df[f"{symbol2}_norm"]

                fig.add_trace(go.Scatter(
                    x=pivot_df.index,
                    y=pivot_df['spread'],
                    mode='lines',
                    name='Spread',
                    line=dict(color='green', dash='dash')
                ))

            fig.update_layout(
                title=f"Normalized Price Comparison ({symbol1} vs {symbol2})",
                xaxis_title="Date",
                yaxis_title="Normalized Price (100 = start)",
                height=500
            )
            #st.plotly_chart(fig, use_container_width=True, key="pairs_comparison_chart")

            
            if 'spread' in pivot_df.columns:
                col_a, col_b, col_c = st.columns(3)

                #col_a.metric("Mean Spread", f"{pivot_df['spread'].mean():.2f}")
                #col_b.metric("Max Spread", f"{pivot_df['spread'].max():.2f}")
                #col_c.metric("Min Spread", f"{pivot_df['spread'].min():.2f}")

                
                correlation = pivot_df[[symbol1, symbol2]].corr().iloc[0, 1]
                #st.metric("Price Correlation", f"{correlation:.4f}")

                
                fig_hist = px.histogram(
                    pivot_df,
                    x='spread',
                    title="Spread Distribution",
                    color_discrete_sequence=['rgba(0, 128, 255, 0.7)']
                )
                fig_hist.add_vline(x=0, line_dash="dash", line_color="red")
                fig_hist.update_layout(height=300)
                #st.plotly_chart(fig_hist, use_container_width=True, key="spread_distribution_chart")
        else:
            st.warning("Could not fetch price data for both symbols")

            

            
        if 'symbol1' in locals() and 'symbol2' in locals() and symbol1 and symbol2:
            st.subheader("Trades Visualization")

            
            symbol1_trades = api_client.get_symbol_trades(market, symbol1, strategy)
            symbol2_trades = api_client.get_symbol_trades(market, symbol2, strategy)

            
            symbol1_filtered_trades = [t for t in symbol1_trades if t.get('paired_symbol') == symbol2]
            symbol2_filtered_trades = [t for t in symbol2_trades if t.get('paired_symbol') == symbol1]

            if symbol1_filtered_trades or symbol2_filtered_trades:
                
                all_trades = pd.DataFrame([
                    {
                        'symbol': t['symbol'],
                        'entry_date': pd.to_datetime(t['entry_date']),
                        'entry_price': t['entry_price'],
                        'exit_date': pd.to_datetime(t['exit_date']),
                        'exit_price': t['exit_price'],
                        'position_type': t['position_type'],
                        'paired_symbol': t['paired_symbol'],
                        'exit_type': t.get('exit_type', 'unknown'),
                        'performance': t.get('performance', 0)
                    }
                    for t in symbol1_filtered_trades + symbol2_filtered_trades
                ])

                if not all_trades.empty:
                    
                    total_trades = len(all_trades)
                    profit_trades = len(all_trades[all_trades['exit_type'] == 'profit'])
                    loss_trades = len(all_trades[all_trades['exit_type'] == 'loss'])
                    breakeven_trades = len(all_trades[all_trades['exit_type'] == 'break-even'])

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total Trades", total_trades)
                    col2.metric("Profit Trades", profit_trades)
                    col3.metric("Loss Trades", loss_trades)
                    col4.metric("Break-Even", breakeven_trades)

                    
                    active_trade_dates = []
                    for _, trade in all_trades.iterrows():
                        active_trade_dates.append(trade['entry_date'])
                        active_trade_dates.append(trade['exit_date'])

                    if active_trade_dates:
                        earliest_trade = min(active_trade_dates)
                        latest_trade = max(active_trade_dates)

                        
                        trade_timespan = (latest_trade - earliest_trade).days
                        buffer_days = max(trade_timespan * 0.15, 7)  
                        trade_view_start = earliest_trade - pd.Timedelta(days=buffer_days)
                        trade_view_end = latest_trade + pd.Timedelta(days=buffer_days)

                        
                        view_option = st.radio(
                            "Anzeige-Option",
                            ["Nur aktive Trade-Zeiträume", "Alle Daten"],
                            horizontal=True
                        )

                        
                        colors = {
                            'profit': 'green',
                            'loss': 'red',
                            'break-even': 'yellow',
                            'unknown': 'gray'
                        }

                        
                        if 'pivot_df' in locals() and not pivot_df.empty:
                            
                            if view_option == "Nur aktive Trade-Zeiträume":
                                filtered_df = pivot_df.loc[(pivot_df.index >= trade_view_start) &
                                                           (pivot_df.index <= trade_view_end)].copy()
                            else:
                                filtered_df = pivot_df.copy()



                            
                            fig_symbol1 = go.Figure()

                            
                            exit_types_shown = {exit_type: True for exit_type in colors.keys()}

                            
                            fig_symbol1.add_trace(go.Scatter(
                                x=filtered_df.index,
                                y=filtered_df[symbol1],
                                mode='lines',
                                name=f"{symbol1} Price",
                                line=dict(color='gray', width=2),
                                hoverinfo='text',
                                hovertext=[f"Date: {d.strftime('%Y-%m-%d')}<br>{symbol1}: {p:.2f}"
                                           for d, p in zip(filtered_df.index, filtered_df[symbol1])]
                            ))

                            
                            s1_trades = all_trades[all_trades['symbol'] == symbol1]
                            for idx, (_, trade) in enumerate(s1_trades.iterrows()):
                                
                                if view_option == "Nur aktive Trade-Zeiträume" and not (
                                        (trade['entry_date'] >= trade_view_start and trade[
                                            'entry_date'] <= trade_view_end) or
                                        (trade['exit_date'] >= trade_view_start and trade[
                                            'exit_date'] <= trade_view_end)
                                ):
                                    continue

                                
                                fig_symbol1.add_trace(go.Scatter(
                                    x=[trade['entry_date']],
                                    y=[trade['entry_price']],
                                    mode='markers',
                                    marker=dict(
                                        symbol='triangle-up' if trade['position_type'] == 'long' else 'triangle-down',
                                        size=14,
                                        color='blue',
                                        line=dict(width=1.5, color='black')
                                    ),
                                    name=f"{trade['position_type'].title()} Entry",
                                    hoverinfo='text',
                                    hovertext=f"Entry: {trade['entry_date'].strftime('%Y-%m-%d')}<br>"
                                              f"Symbol: {symbol1}<br>"
                                              f"Price: {trade['entry_price']:.2f}<br>"
                                              f"Type: {trade['position_type']}",
                                    showlegend=idx == 0  
                                ))

                                
                                fig_symbol1.add_trace(go.Scatter(
                                    x=[trade['exit_date']],
                                    y=[trade['exit_price']],
                                    mode='markers',
                                    marker=dict(
                                        symbol='circle',
                                        size=12,
                                        color=colors.get(trade['exit_type'], 'gray'),
                                        line=dict(width=1.5, color='black')
                                    ),
                                    name=f"{trade['exit_type'].title()} Exit",
                                    hoverinfo='text',
                                    hovertext=f"Exit: {trade['exit_date'].strftime('%Y-%m-%d')}<br>"
                                              f"Symbol: {symbol1}<br>"
                                              f"Price: {trade['exit_price']:.2f}<br>"
                                              f"Type: {trade['exit_type']}<br>"
                                              f"Perf: {trade['performance']:.2%}",
                                    showlegend=exit_types_shown.get(trade['exit_type'], True)
                                    
                                ))

                                
                                if exit_types_shown.get(trade['exit_type'], True):
                                    exit_types_shown[trade['exit_type']] = False

                                
                                fig_symbol1.add_trace(go.Scatter(
                                    x=[trade['entry_date'], trade['exit_date']],
                                    y=[trade['entry_price'], trade['exit_price']],
                                    mode='lines',
                                    line=dict(
                                        color=colors.get(trade['exit_type'], 'gray'),
                                        width=1.5,
                                        dash='dot'
                                    ),
                                    showlegend=False
                                ))

                            
                            fig_symbol1.update_layout(
                                title=f"{symbol1} Trades Timeline",
                                xaxis=dict(
                                    title="Date",
                                    rangeslider=dict(visible=False),
                                    type="date"
                                ),
                                yaxis=dict(
                                    title=f"{symbol1} Price"
                                ),
                                height=400,
                                hovermode="closest",
                                margin=dict(l=40, r=40, t=50, b=40),
                                plot_bgcolor='rgba(255,255,255,1)'
                            )

                            
                            fig_symbol1.update_layout(
                                updatemenus=[
                                    dict(
                                        type="buttons",
                                        showactive=False,
                                        buttons=[
                                            dict(
                                                label="Reset Zoom",
                                                method="relayout",
                                                args=[{"xaxis.autorange": True, "yaxis.autorange": True}]
                                            )
                                        ],
                                        x=0.05,
                                        y=-0.15,
                                        xanchor="left",
                                        yanchor="bottom"
                                    )
                                ]
                            )

                            st.plotly_chart(fig_symbol1, use_container_width=True)

                            
                            fig_symbol2 = go.Figure()

                            
                            exit_types_shown = {exit_type: True for exit_type in colors.keys()}

                            
                            fig_symbol2.add_trace(go.Scatter(
                                x=filtered_df.index,
                                y=filtered_df[symbol2],
                                mode='lines',
                                name=f"{symbol2} Price",
                                line=dict(color='gray', width=2),
                                hoverinfo='text',
                                hovertext=[f"Date: {d.strftime('%Y-%m-%d')}<br>{symbol2}: {p:.2f}"
                                           for d, p in zip(filtered_df.index, filtered_df[symbol2])]
                            ))

                            
                            s2_trades = all_trades[all_trades['symbol'] == symbol2]
                            for idx, (_, trade) in enumerate(s2_trades.iterrows()):
                                
                                if view_option == "Nur aktive Trade-Zeiträume" and not (
                                        (trade['entry_date'] >= trade_view_start and trade[
                                            'entry_date'] <= trade_view_end) or
                                        (trade['exit_date'] >= trade_view_start and trade[
                                            'exit_date'] <= trade_view_end)
                                ):
                                    continue

                                
                                fig_symbol2.add_trace(go.Scatter(
                                    x=[trade['entry_date']],
                                    y=[trade['entry_price']],
                                    mode='markers',
                                    marker=dict(
                                        symbol='triangle-up' if trade['position_type'] == 'long' else 'triangle-down',
                                        size=14,
                                        color='blue',  
                                        line=dict(width=1.5, color='black')
                                    ),
                                    name=f"{trade['position_type'].title()} Entry",
                                    hoverinfo='text',
                                    hovertext=f"Entry: {trade['entry_date'].strftime('%Y-%m-%d')}<br>"
                                              f"Symbol: {symbol2}<br>"
                                              f"Price: {trade['entry_price']:.2f}<br>"
                                              f"Type: {trade['position_type']}",
                                    showlegend=idx == 0  
                                ))

                                
                                fig_symbol2.add_trace(go.Scatter(
                                    x=[trade['exit_date']],
                                    y=[trade['exit_price']],
                                    mode='markers',
                                    marker=dict(
                                        symbol='circle',
                                        size=12,
                                        color=colors.get(trade['exit_type'], 'gray'),
                                        line=dict(width=1.5, color='black')
                                    ),
                                    name=f"{trade['exit_type'].title()} Exit",
                                    hoverinfo='text',
                                    hovertext=f"Exit: {trade['exit_date'].strftime('%Y-%m-%d')}<br>"
                                              f"Symbol: {symbol2}<br>"
                                              f"Price: {trade['exit_price']:.2f}<br>"
                                              f"Type: {trade['exit_type']}<br>"
                                              f"Perf: {trade['performance']:.2%}",
                                    showlegend=exit_types_shown.get(trade['exit_type'], True)
                                    
                                ))

                                
                                if exit_types_shown.get(trade['exit_type'], True):
                                    exit_types_shown[trade['exit_type']] = False

                                
                                fig_symbol2.add_trace(go.Scatter(
                                    x=[trade['entry_date'], trade['exit_date']],
                                    y=[trade['entry_price'], trade['exit_price']],
                                    mode='lines',
                                    line=dict(
                                        color=colors.get(trade['exit_type'], 'gray'),
                                        width=1.5,
                                        dash='dot'
                                    ),
                                    showlegend=False
                                ))

                            
                            fig_symbol2.update_layout(
                                title=f"{symbol2} Trades Timeline",
                                xaxis=dict(
                                    title="Date",
                                    rangeslider=dict(visible=False),
                                    type="date"
                                ),
                                yaxis=dict(
                                    title=f"{symbol2} Price"
                                ),
                                height=400,
                                hovermode="closest",
                                margin=dict(l=40, r=40, t=50, b=40),
                                plot_bgcolor='rgba(255,255,255,1)'
                            )

                            
                            fig_symbol2.update_layout(
                                updatemenus=[
                                    dict(
                                        type="buttons",
                                        showactive=False,
                                        buttons=[
                                            dict(
                                                label="Reset Zoom",
                                                method="relayout",
                                                args=[{"xaxis.autorange": True, "yaxis.autorange": True}]
                                            )
                                        ],
                                        x=0.05,
                                        y=-0.15,
                                        xanchor="left",
                                        yanchor="bottom"
                                    )
                                ]
                            )

                            st.plotly_chart(fig_symbol2, use_container_width=True)


                            
                            st.subheader("Trades Details")
                            trades_display = all_trades.copy()
                            trades_display['entry_date'] = trades_display['entry_date'].dt.strftime('%Y-%m-%d')
                            trades_display['exit_date'] = trades_display['exit_date'].dt.strftime('%Y-%m-%d')
                            trades_display['performance'] = trades_display['performance'].map('{:.2%}'.format)

                            st.dataframe(
                                trades_display.sort_values('entry_date'),
                                use_container_width=True,
                                hide_index=True,
                                column_order=['symbol', 'paired_symbol', 'position_type', 'entry_date', 'entry_price',
                                              'exit_date', 'exit_price', 'exit_type', 'performance']
                            )
                        else:
                            st.warning("Could not create trades timeline due to missing price data")
                    else:
                        st.info("No trade dates found")
                else:
                    st.info("No trades found for this pair")
            else:
                st.info("No paired trades found between these symbols")