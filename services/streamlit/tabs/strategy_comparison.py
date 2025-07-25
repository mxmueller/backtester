import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from api import APIClient
from config import Config
import io
from datetime import datetime


def render(api_client: APIClient, config: Config):
    st.header("Strategy Comparison")

    market = config.get_market()
    if not market:
        st.warning("Market must be selected")
        return
    
    strategies_data = api_client.get_market_strategies(market)

    if not strategies_data or "strategies" not in strategies_data or not strategies_data["strategies"]:
        st.warning(f"No strategies available for {market}")
        return

    strategies = strategies_data["strategies"]
    strategy_options = [s["version"] for s in strategies]

    
    selected_strategies = st.multiselect(
        "Select Strategies to Compare",
        options=strategy_options,
        default=strategy_options[:min(2, len(strategy_options))]
    )

    if len(selected_strategies) < 2:
        st.info("Please select at least 2 strategies to compare")
        return

    trading_params = config.get_trading_params()

    tabs = st.tabs(["Performance Metrics", "Equity Curves", "Returns Distribution", "Drawdowns", "Pair Analysis", "Export"])

    with tabs[0]:
        st.subheader("Performance Comparison")

        performance_data = {}
        for strategy in selected_strategies:
            data = api_client.get_trades_performance(market, strategy, trading_params)
            if data and "performance" in data:
                performance_data[strategy] = data["performance"]

        if not performance_data:
            st.warning("Failed to fetch performance data for selected strategies")
            return
        
        metrics = []
        for strategy, perf in performance_data.items():
            metrics.append({
                "Strategy": strategy,
                "Total Return": f"{perf.get('final_performance', 0):.2%}" if 'final_performance' in perf else "-",
                "Sharpe Ratio": f"{perf.get('sharpe_ratio', 0):.2f}" if 'sharpe_ratio' in perf else "-",
                "Max Drawdown": f"{perf.get('max_drawdown', 0):.2%}" if 'max_drawdown' in perf else "-",
                "Win Rate": f"{perf.get('net_performance', {}).get('win_rate', 0):.2%}" if 'net_performance' in perf else "-",
                "Total Trades": perf.get('total_trades', 0),
                "Profitable Days": f"{perf.get('profitable_days', 0)}/{perf.get('total_days', 0)}"
            })

        metrics_df = pd.DataFrame(metrics)
        st.dataframe(metrics_df, hide_index=True, use_container_width=True)

        
        key_metrics = ["Total Return", "Sharpe Ratio", "Max Drawdown", "Win Rate"]
        chart_data = []

        for strategy, perf in performance_data.items():
            chart_data.append({
                "Strategy": strategy,
                "Metric": "Total Return",
                "Value": perf.get('final_performance', 0) if 'final_performance' in perf else 0
            })
            chart_data.append({
                "Strategy": strategy,
                "Metric": "Sharpe Ratio",
                "Value": perf.get('sharpe_ratio', 0) if 'sharpe_ratio' in perf else 0
            })
            chart_data.append({
                "Strategy": strategy,
                "Metric": "Max Drawdown",
                "Value": perf.get('max_drawdown', 0) if 'max_drawdown' in perf else 0
            })
            chart_data.append({
                "Strategy": strategy,
                "Metric": "Win Rate",
                "Value": perf.get('net_performance', {}).get('win_rate', 0) if 'net_performance' in perf else 0
            })

        chart_df = pd.DataFrame(chart_data)

        
        for metric in key_metrics:
            metric_df = chart_df[chart_df["Metric"] == metric]

            if not metric_df.empty:
                title = f"Comparison by {metric}"
                if metric == "Max Drawdown":
                    
                    metric_df = metric_df.copy()
                    metric_df.loc[:, "Value"] = -metric_df["Value"]
                    title += " (Inverted - Lower is Better)"

                fig = px.bar(
                    metric_df,
                    x="Strategy",
                    y="Value",
                    title=title,
                    color="Strategy"
                )

                if metric in ["Total Return", "Win Rate"]:
                    fig.update_layout(yaxis_tickformat=".1%")

                st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        st.subheader("Equity Curves Comparison")

        timeseries_data = {}
        for strategy in selected_strategies:
            data = api_client.get_trades_performance_timeseries(market, strategy, trading_params)
            if data and "timeseries" in data:
                ts_df = pd.DataFrame.from_dict(data["timeseries"], orient='index')
                if not ts_df.empty:
                    ts_df.index = pd.to_datetime(ts_df.index)
                    ts_df = ts_df.sort_index()
                    ts_df["strategy"] = strategy
                    timeseries_data[strategy] = ts_df

        if not timeseries_data:
            st.warning("Failed to fetch timeseries data for selected strategies")
            return
        
        fig = go.Figure()

        for strategy, ts_df in timeseries_data.items():
            if "total_capital" in ts_df.columns:
                fig.add_trace(go.Scatter(
                    x=ts_df.index,
                    y=ts_df["total_capital"],
                    mode="lines",
                    name=strategy
                ))

        fig.update_layout(
            title="Portfolio Equity Curves",
            xaxis_title="Date",
            yaxis_title="Capital",
            height=500
        )

        if "initial_capital" in trading_params:
            fig.add_hline(
                y=trading_params["initial_capital"],
                line_dash="dash",
                line_color="red",
                annotation_text="Initial Capital"
            )

        st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        st.subheader("Returns Distribution")

        daily_returns = {}
        for strategy, ts_df in timeseries_data.items():
            if "total_capital" in ts_df.columns and len(ts_df) > 1:
                returns = ts_df["total_capital"].pct_change().dropna()
                daily_returns[strategy] = returns

        if not daily_returns:
            st.warning("Insufficient data to calculate returns distribution")
            return

        
        fig = go.Figure()

        for strategy, returns in daily_returns.items():
            fig.add_trace(go.Histogram(
                x=returns,
                name=strategy,
                opacity=0.7,
                nbinsx=50
            ))

        fig.update_layout(
            title="Daily Returns Distribution",
            xaxis_title="Daily Return",
            yaxis_title="Frequency",
            barmode="overlay",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

        
        stats = []
        for strategy, returns in daily_returns.items():
            stats.append({
                "Strategy": strategy,
                "Mean Return": f"{returns.mean():.4%}",
                "Std Dev": f"{returns.std():.4%}",
                "Min Return": f"{returns.min():.4%}",
                "Max Return": f"{returns.max():.4%}",
                "Positive Days": f"{(returns > 0).sum()}/{len(returns)} ({(returns > 0).mean():.2%})"
            })

        stats_df = pd.DataFrame(stats)
        st.dataframe(stats_df, hide_index=True, use_container_width=True)

    with tabs[3]:
        st.subheader("Drawdowns Analysis")

        max_drawdowns = {}
        drawdown_series = {}

        for strategy, ts_df in timeseries_data.items():
            if "total_capital" in ts_df.columns and len(ts_df) > 0:
                
                running_max = ts_df["total_capital"].cummax()

                
                drawdown = (ts_df["total_capital"] - running_max) / running_max
                drawdown_series[strategy] = drawdown

                
                max_drawdowns[strategy] = drawdown.min()

        if not drawdown_series:
            st.warning("Insufficient data to calculate drawdowns")
            return

        
        fig = go.Figure()

        for strategy, drawdown in drawdown_series.items():
            fig.add_trace(go.Scatter(
                x=drawdown.index,
                y=drawdown * 100,  
                mode="lines",
                name=strategy
            ))

        fig.update_layout(
            title="Drawdown Over Time",
            xaxis_title="Date",
            yaxis_title="Drawdown (%)",
            height=500
        )

        fig.update_yaxes(autorange="reversed")  

        st.plotly_chart(fig, use_container_width=True)

        
        drawdown_data = [{"Strategy": s, "Max Drawdown": d * 100} for s, d in max_drawdowns.items()]
        drawdown_df = pd.DataFrame(drawdown_data)

        fig_bar = px.bar(
            drawdown_df,
            x="Strategy",
            y="Max Drawdown",
            title="Maximum Drawdown Comparison",
            color="Strategy"
        )

        fig_bar.update_layout(height=400)
        fig_bar.update_yaxes(autorange="reversed")  

        st.plotly_chart(fig_bar, use_container_width=True)

    with tabs[4]:
        st.subheader("Pair Analysis Across Strategies")

        
        windows_by_strategy = {}
        all_windows = set()

        for strategy in selected_strategies:
            windows_data = api_client.get_available_windows(market, strategy)
            if windows_data and "windows" in windows_data:
                strategy_windows = windows_data["windows"]
                windows_by_strategy[strategy] = strategy_windows
                all_windows.update(strategy_windows)

        if not all_windows:
            st.warning("No trading windows available for the selected strategies")
            return

        
        selected_window = st.selectbox(
            "Select Trading Window for Comparison",
            sorted(list(all_windows)),
            format_func=lambda x: f"Window {x}",
            key="strategy_pairs_window_selector"
        )

        if not selected_window:
            st.info("Please select a trading window")
            return

        
        pairs_data_by_strategy = {}
        all_pairs = set()

        for strategy in selected_strategies:
            if strategy in windows_by_strategy and selected_window in windows_by_strategy[strategy]:
                pairs_data = api_client.get_pairs_for_window(market, selected_window, strategy)

                window_key = str(selected_window)
                window_data = pairs_data.get(window_key, {})

                if not window_data and selected_window in pairs_data:
                    window_data = pairs_data.get(selected_window, {})

                if window_data and "pairs" in window_data:
                    pairs_list = window_data["pairs"]
                    pairs_dict = {}

                    for pair_data in pairs_list:
                        pair_tuple = tuple(sorted(pair_data["pair"]))
                        pairs_dict[pair_tuple] = {
                            "trades": pair_data["trades"],
                            "pair_str": f"{pair_tuple[0]} - {pair_tuple[1]}"
                        }
                        all_pairs.add(pair_tuple)

                    pairs_data_by_strategy[strategy] = pairs_dict

        if not pairs_data_by_strategy:
            st.warning("No pairs data available for the selected window and strategies")
            return

        
        comparison_data = []

        for pair in sorted(all_pairs):
            pair_row = {"Pair": f"{pair[0]} - {pair[1]}"}

            for strategy in selected_strategies:
                if strategy in pairs_data_by_strategy and pair in pairs_data_by_strategy[strategy]:
                    pair_row[f"{strategy} (trades)"] = pairs_data_by_strategy[strategy][pair]["trades"]
                else:
                    pair_row[f"{strategy} (trades)"] = 0

            comparison_data.append(pair_row)

        comparison_df = pd.DataFrame(comparison_data)

        
        st.subheader(f"Pairs Comparison for Window {selected_window}")

        
        if len(selected_strategies) > 0:
            trade_cols = [f"{strategy} (trades)" for strategy in selected_strategies]
            has_trades = comparison_df[trade_cols].sum(axis=1) > 0
            filtered_df = comparison_df[has_trades]
        else:
            filtered_df = comparison_df

        st.dataframe(
            filtered_df.sort_values("Pair"),
            use_container_width=True,
            hide_index=True,
            key="strategy_pairs_comparison_table"
        )

        st.subheader("Common Pairs Analysis")
    
        common_pairs_across_strategies = set()
        if len(selected_strategies) > 0 and all(strategy in pairs_data_by_strategy for strategy in selected_strategies):
            
            common_pairs_across_strategies = set(pairs_data_by_strategy[selected_strategies[0]].keys())
            
            for strategy in selected_strategies[1:]:
                common_pairs_across_strategies = common_pairs_across_strategies.intersection(
                    set(pairs_data_by_strategy[strategy].keys())
                )

        if common_pairs_across_strategies:
            st.write(f"Found {len(common_pairs_across_strategies)} pairs that appear in all selected strategies")
         
            common_pairs_data = []

            for pair in sorted(common_pairs_across_strategies):
                pair_str = f"{pair[0]} - {pair[1]}"
                pair_row = {"Pair": pair_str}

                
                for strategy in selected_strategies:
                    pair_row[f"{strategy} (trades)"] = pairs_data_by_strategy[strategy][pair]["trades"]

                common_pairs_data.append(pair_row)
        
            common_pairs_df = pd.DataFrame(common_pairs_data)
            st.dataframe(
                common_pairs_df,
                use_container_width=True,
                hide_index=True,
                key="common_pairs_table"
            )
         
            if common_pairs_data:
                selected_common_pair = st.selectbox(
                    "Select a common pair for detailed analysis",
                    options=[row["Pair"] for row in common_pairs_data],
                    key="common_pair_selector"
                )

                if selected_common_pair:
                    st.subheader(f"Detailed Comparison for {selected_common_pair}")
                    pair_symbols = selected_common_pair.split(" - ")
                    if len(pair_symbols) == 2:
                        symbol1, symbol2 = pair_symbols
               
                        detailed_perf = []

                        for strategy in selected_strategies:
                            pair_perf = api_client.get_pair_performance(
                                market,
                                symbol1,
                                symbol2,
                                strategy,
                                window=selected_window,
                                trading_params=trading_params
                            )

                            if pair_perf and "net_performance" in pair_perf:
                                net_perf = pair_perf["net_performance"]

                                
                                perf_metrics = {
                                    "Strategy": strategy,
                                    "Total Return": net_perf.get("total_performance", 0),
                                    "Win Rate": net_perf.get("win_rate", 0),
                                    "Total Trades": net_perf.get("total_trades", 0),
                                    "Avg Trade Return": net_perf.get("avg_performance", 0)
                                }

                                
                                if strategy in pairs_data_by_strategy and pair in pairs_data_by_strategy[strategy]:
                                    perf_metrics["Trades in Window"] = pairs_data_by_strategy[strategy][pair]["trades"]

                                detailed_perf.append(perf_metrics)

                        if detailed_perf:
                            
                            detailed_df = pd.DataFrame(detailed_perf)
                         
                            for metric in ["Total Return", "Win Rate", "Avg Trade Return"]:
                                fig = px.bar(
                                    detailed_df,
                                    x="Strategy",
                                    y=metric,
                                    title=f"{metric} by Strategy for {selected_common_pair}",
                                    color="Strategy"
                                )

                                
                                if metric in ["Total Return", "Win Rate", "Avg Trade Return"]:
                                    fig.update_layout(yaxis_tickformat=".1%")

                                st.plotly_chart(fig, use_container_width=True)
                        
                            display_df = detailed_df.copy()
                            for col in ["Total Return", "Win Rate", "Avg Trade Return"]:
                                display_df[col] = display_df[col].apply(lambda x: f"{x:.2%}")

                            st.dataframe(
                                display_df,
                                use_container_width=True,
                                hide_index=True,
                                key="common_pair_detailed_table"
                            )

                            if all("max_gain" in pair_perf.get("net_performance", {}) and "max_loss" in pair_perf.get(
                                    "net_performance", {})
                                   for pair_perf in [api_client.get_pair_performance(
                                market, symbol1, symbol2, strategy, window=selected_window,
                                trading_params=trading_params
                            ) for strategy in selected_strategies]):

                                max_metrics = []
                                for strategy in selected_strategies:
                                    pair_perf = api_client.get_pair_performance(
                                        market, symbol1, symbol2, strategy, window=selected_window,
                                        trading_params=trading_params
                                    )
                                    if pair_perf and "net_performance" in pair_perf:
                                        
                                        max_metrics.append({
                                            "Strategy": strategy,
                                            "Metric": "Max Gain",
                                            "Value": float(pair_perf["net_performance"].get("max_gain", 0))
                                        })
                                        max_metrics.append({
                                            "Strategy": strategy,
                                            "Metric": "Max Loss",
                                            "Value": float(abs(pair_perf["net_performance"].get("max_loss", 0)))
                                            
                                        })

                                if max_metrics:
                                    max_df = pd.DataFrame(max_metrics)
                                    fig = px.bar(
                                        max_df,
                                        x="Strategy",
                                        y="Value",
                                        color="Metric",
                                        barmode="group",
                                        title="Maximum Gains and Losses by Strategy"
                                    )
                                    fig.update_layout(yaxis_tickformat=".1%")
                                    st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Could not fetch performance data for this pair across all strategies")
        else:
            st.info("No common pairs found across all selected strategies")

            
            if len(selected_strategies) > 2:
                min_strategies = st.slider(
                    "Show pairs appearing in at least X strategies",
                    min_value=2,
                    max_value=len(selected_strategies),
                    value=2
                )
            elif len(selected_strategies) == 2:
                min_strategies = 2
          
                pair_strategy_count = {}
                all_pairs_set = set()

                for strategy, pairs_dict in pairs_data_by_strategy.items():
                    for pair in pairs_dict.keys():
                        all_pairs_set.add(pair)
                        if pair not in pair_strategy_count:
                            pair_strategy_count[pair] = 0
                        pair_strategy_count[pair] += 1

                
                filtered_pairs = [pair for pair, count in pair_strategy_count.items() if count >= min_strategies]

                if filtered_pairs:
                    st.write(f"Found {len(filtered_pairs)} pairs that appear in at least {min_strategies} strategies")

                    
                    filtered_data = []
                    for pair in sorted(filtered_pairs):
                        pair_str = f"{pair[0]} - {pair[1]}"
                        pair_row = {
                            "Pair": pair_str,
                            "Strategies": pair_strategy_count[pair]
                        }

                        
                        for strategy in selected_strategies:
                            if strategy in pairs_data_by_strategy and pair in pairs_data_by_strategy[strategy]:
                                pair_row[f"{strategy} (trades)"] = pairs_data_by_strategy[strategy][pair]["trades"]
                            else:
                                pair_row[f"{strategy} (trades)"] = 0

                        filtered_data.append(pair_row)

                    filtered_df = pd.DataFrame(filtered_data)
                    st.dataframe(
                        filtered_df.sort_values("Strategies", ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        key="filtered_pairs_table"
                    )

        
        st.subheader("Pair Distribution Statistics")

        strategy_unique_pairs = {}
        common_pairs = set()

        for i, strategy in enumerate(selected_strategies):
            if strategy in pairs_data_by_strategy:
                strategy_pairs = set(pairs_data_by_strategy[strategy].keys())
                strategy_unique_pairs[strategy] = strategy_pairs

                if i == 0:
                    common_pairs = strategy_pairs
                else:
                    common_pairs = common_pairs.intersection(strategy_pairs)

        
        unique_counts = {}
        for strategy in selected_strategies:
            if strategy in strategy_unique_pairs:
                unique_to_strategy = strategy_unique_pairs[strategy].difference(
                    set().union(*[p for s, p in strategy_unique_pairs.items() if s != strategy])
                )
                unique_counts[strategy] = len(unique_to_strategy)

        stats_data = []

        for strategy in selected_strategies:
            if strategy in pairs_data_by_strategy:
                total_pairs = len(pairs_data_by_strategy[strategy])
                unique_pairs = unique_counts.get(strategy, 0)

                stats_data.append({
                    "Strategy": strategy,
                    "Total Pairs": total_pairs,
                    "Unique Pairs": unique_pairs,
                    "Common Pairs": len(common_pairs),
                    "% Unique": f"{unique_pairs / total_pairs * 100:.1f}%" if total_pairs > 0 else "0.0%"
                })

        stats_df = pd.DataFrame(stats_data)
        st.dataframe(
            stats_df,
            use_container_width=True,
            hide_index=True,
            key="strategy_pairs_stats_table"
        )

        if len(selected_strategies) > 1:
            st.subheader("Pair Overlap Analysis")

            
            overlap_data = []
            for i, strategy1 in enumerate(selected_strategies):
                if strategy1 not in strategy_unique_pairs:
                    continue

                s1_pairs = strategy_unique_pairs[strategy1]

                for strategy2 in selected_strategies[i + 1:]:
                    if strategy2 not in strategy_unique_pairs:
                        continue

                    s2_pairs = strategy_unique_pairs[strategy2]
                    overlap = len(s1_pairs.intersection(s2_pairs))

                    overlap_data.append({
                        "Strategy 1": strategy1,
                        "Strategy 2": strategy2,
                        "Overlap": overlap,
                        "Only in Strategy 1": len(s1_pairs.difference(s2_pairs)),
                        "Only in Strategy 2": len(s2_pairs.difference(s1_pairs)),
                    })

            if overlap_data:
                overlap_df = pd.DataFrame(overlap_data)
                st.dataframe(
                    overlap_df,
                    use_container_width=True,
                    hide_index=True,
                    key="pair_overlap_table"
                )

                
                st.subheader("Top Pairs by Strategy")

                for strategy in selected_strategies:
                    if strategy in pairs_data_by_strategy:
                        pairs = pairs_data_by_strategy[strategy]

                        if pairs:
                            pairs_df = pd.DataFrame([
                                {"Pair": p["pair_str"], "Trades": p["trades"]}
                                for p in pairs.values()
                            ])

                            pairs_df = pairs_df.sort_values("Trades", ascending=False).head(10)

                            fig = px.bar(
                                pairs_df,
                                x="Pair",
                                y="Trades",
                                title=f"Top 10 Pairs for {strategy}",
                                color_discrete_sequence=[px.colors.qualitative.Plotly[
                                                             selected_strategies.index(strategy) % len(
                                                                 px.colors.qualitative.Plotly)]]
                            )
                            fig.update_layout(
                                xaxis_tickangle=-45,
                                height=400
                            )
                            st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("Please select a pair to compare performance")
        else:
            st.info("No pairs available for comparison")

    # NEW EXPORT TAB
    with tabs[5]:
        st.subheader("Data Export for Statistical Analysis")
        
        st.markdown("""
        **Export raw data for detailed statistical analysis including:**
        - Total Return & Sharpe Ratio comparison
        - Maximum Drawdown analysis
        - Significance tests between approaches
        - Consistency analysis (how often one strategy outperformed another)
        - Trade metrics (Win Rate, Number of Trades)
        - Transaction cost impact analysis
        """)

        if st.button("🔄 Refresh Data for Export", use_container_width=True):
            st.rerun()

        # Collect all performance data for selected strategies
        export_data = {}
        timeseries_data_export = {}
        
        for strategy in selected_strategies:
            # Get performance metrics
            perf_data = api_client.get_trades_performance(market, strategy, trading_params)
            export_data[strategy] = perf_data
            
            # Get timeseries data
            ts_data = api_client.get_trades_performance_timeseries(market, strategy, trading_params)
            timeseries_data_export[strategy] = ts_data

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 Performance Summary Export")
            
            if export_data:
                # Create comprehensive performance summary
                summary_data = []
                
                for strategy, data in export_data.items():
                    if data and "performance" in data:
                        perf = data["performance"]
                        
                        row = {
                            "strategy": strategy,
                            "market": market,
                            "total_trades": perf.get("total_trades", 0),
                            "profitable_days": perf.get("profitable_days", 0),
                            "total_days": perf.get("total_days", 0),
                            "max_drawdown": perf.get("max_drawdown", 0),
                            "sharpe_ratio": perf.get("sharpe_ratio", None),
                            "final_performance": perf.get("final_performance", 0),
                        }
                        
                        # Portfolio metrics
                        if "portfolio" in perf:
                            portfolio = perf["portfolio"]
                            row.update({
                                "initial_capital": portfolio.get("initial_capital", 0),
                                "final_capital": portfolio.get("final_capital", 0),
                                "max_capital": portfolio.get("max_capital", 0),
                                "min_capital": portfolio.get("min_capital", 0),
                            })
                        
                        # Net performance metrics
                        if "net_performance" in perf:
                            net_perf = perf["net_performance"]
                            row.update({
                                "total_performance": net_perf.get("total_performance", 0),
                                "avg_performance": net_perf.get("avg_performance", 0),
                                "win_rate": net_perf.get("win_rate", 0),
                                "max_gain": net_perf.get("max_gain", 0),
                                "max_loss": net_perf.get("max_loss", 0),
                                "profitable_trades": net_perf.get("profitable_trades", 0),
                            })
                        
                        # Cost metrics
                        if "costs" in perf:
                            costs = perf["costs"]
                            row.update({
                                "total_costs": costs.get("total_costs", 0),
                                "avg_cost_per_trade": costs.get("avg_cost_per_trade", 0),
                            })
                        
                        # Trading parameters
                        row.update({
                            "initial_capital_param": trading_params.get("initial_capital", 0),
                            "position_size_percent": trading_params.get("position_size_percent", 0),
                            "fixed_commission": trading_params.get("fixed_commission", 0),
                            "variable_fee": trading_params.get("variable_fee", 0),
                            "bid_ask_spread": trading_params.get("bid_ask_spread", 0),
                            "risk_free_rate": trading_params.get("risk_free_rate", 0),
                        })
                        
                        summary_data.append(row)
                
                if summary_data:
                    summary_df = pd.DataFrame(summary_data)
                    
                    st.write(f"**{len(summary_data)} strategies** ready for export")
                    
                    # Show preview
                    with st.expander("📋 Preview Performance Summary"):
                        st.dataframe(summary_df, use_container_width=True)
                    
                    # Download button
                    csv_buffer = io.StringIO()
                    summary_df.to_csv(csv_buffer, index=False)
                    
                    st.download_button(
                        label="📥 Download Performance Summary (CSV)",
                        data=csv_buffer.getvalue(),
                        file_name=f"{market}_strategy_comparison_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.warning("No performance data available for export")

        with col2:
            st.subheader("📈 Timeseries Data Export")
            
            if timeseries_data_export:
                # Create combined timeseries dataset
                all_timeseries = []
                
                for strategy, data in timeseries_data_export.items():
                    if data and "timeseries" in data:
                        ts_df = pd.DataFrame.from_dict(data["timeseries"], orient='index')
                        
                        if not ts_df.empty:
                            ts_df['strategy'] = strategy
                            ts_df['market'] = market
                            ts_df['date'] = ts_df.index
                            ts_df = ts_df.reset_index(drop=True)
                            all_timeseries.append(ts_df)
                
                if all_timeseries:
                    combined_ts = pd.concat(all_timeseries, ignore_index=True)
                    
                    st.write(f"**{len(combined_ts)} data points** across all strategies")
                    
                    # Show preview
                    with st.expander("📋 Preview Timeseries Data"):
                        st.dataframe(combined_ts.head(10), use_container_width=True)
                    
                    # Download button
                    csv_buffer = io.StringIO()
                    combined_ts.to_csv(csv_buffer, index=False)
                    
                    st.download_button(
                        label="📥 Download Timeseries Data (CSV)",
                        data=csv_buffer.getvalue(),
                        file_name=f"{market}_strategy_timeseries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                    # Calculate daily returns for statistical analysis
                    if st.button("📊 Prepare Returns Data for Significance Testing"):
                        returns_data = []
                        
                        for strategy in selected_strategies:
                            strategy_data = combined_ts[combined_ts['strategy'] == strategy].copy()
                            
                            if 'total_capital' in strategy_data.columns and len(strategy_data) > 1:
                                strategy_data = strategy_data.sort_values('date')
                                strategy_data['daily_return'] = strategy_data['total_capital'].pct_change()
                                
                                for _, row in strategy_data.iterrows():
                                    if not pd.isna(row['daily_return']):
                                        returns_data.append({
                                            'date': row['date'],
                                            'strategy': strategy,
                                            'daily_return': row['daily_return'],
                                            'total_capital': row['total_capital'],
                                            'market': market
                                        })
                        
                        if returns_data:
                            returns_df = pd.DataFrame(returns_data)
                            
                            csv_buffer = io.StringIO()
                            returns_df.to_csv(csv_buffer, index=False)
                            
                            st.download_button(
                                label="📥 Download Daily Returns for Statistical Tests (CSV)",
                                data=csv_buffer.getvalue(),
                                file_name=f"{market}_daily_returns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                else:
                    st.warning("No timeseries data available for export")

        st.markdown("---")

        # Pairs analysis export
        st.subheader("🔗 Pairs Analysis Export")
        
        # Window selection for pairs export
        windows_by_strategy_export = {}
        all_windows_export = set()

        for strategy in selected_strategies:
            windows_data = api_client.get_available_windows(market, strategy)
            if windows_data and "windows" in windows_data:
                strategy_windows = windows_data["windows"]
                windows_by_strategy_export[strategy] = strategy_windows
                all_windows_export.update(strategy_windows)

        if all_windows_export:
            selected_window_export = st.selectbox(
                "Select Trading Window for Pairs Export",
                sorted(list(all_windows_export)),
                format_func=lambda x: f"Window {x}",
                key="export_window_selector"
            )

            if selected_window_export and st.button("📊 Generate Pairs Export Data"):
                pairs_export_data = []
                
                for strategy in selected_strategies:
                    if strategy in windows_by_strategy_export and selected_window_export in windows_by_strategy_export[strategy]:
                        pairs_data = api_client.get_pairs_for_window(market, selected_window_export, strategy)
                        
                        window_key = str(selected_window_export)
                        window_data = pairs_data.get(window_key, {})
                        
                        if not window_data and selected_window_export in pairs_data:
                            window_data = pairs_data.get(selected_window_export, {})
                        
                        if window_data and "pairs" in window_data:
                            pairs_list = window_data["pairs"]
                            
                            for pair_data in pairs_list:
                                pair_tuple = tuple(sorted(pair_data["pair"]))
                                
                                # Get detailed pair performance
                                pair_perf = api_client.get_pair_performance(
                                    market,
                                    pair_tuple[0],
                                    pair_tuple[1],
                                    strategy,
                                    window=selected_window_export,
                                    trading_params=trading_params
                                )
                                
                                row = {
                                    "strategy": strategy,
                                    "market": market,
                                    "window": selected_window_export,
                                    "symbol1": pair_tuple[0],
                                    "symbol2": pair_tuple[1],
                                    "pair_name": f"{pair_tuple[0]}-{pair_tuple[1]}",
                                    "trades_in_window": pair_data["trades"],
                                }
                                
                                if pair_perf and "net_performance" in pair_perf:
                                    net_perf = pair_perf["net_performance"]
                                    row.update({
                                        "total_performance": net_perf.get("total_performance", 0),
                                        "avg_performance": net_perf.get("avg_performance", 0),
                                        "win_rate": net_perf.get("win_rate", 0),
                                        "max_gain": net_perf.get("max_gain", 0),
                                        "max_loss": net_perf.get("max_loss", 0),
                                        "profitable_trades": net_perf.get("profitable_trades", 0),
                                        "total_trades": net_perf.get("total_trades", 0),
                                    })
                                
                                if pair_perf and "sharpe_ratio" in pair_perf:
                                    row["sharpe_ratio"] = pair_perf["sharpe_ratio"]
                                
                                if pair_perf and "costs" in pair_perf:
                                    costs = pair_perf["costs"]
                                    row.update({
                                        "total_costs": costs.get("total_costs", 0),
                                        "avg_cost_per_trade": costs.get("avg_cost_per_trade", 0),
                                    })
                                
                                pairs_export_data.append(row)
                
                if pairs_export_data:
                    pairs_df = pd.DataFrame(pairs_export_data)
                    
                    st.success(f"Generated {len(pairs_export_data)} pair records for export")
                    
                    with st.expander("📋 Preview Pairs Data"):
                        st.dataframe(pairs_df.head(10), use_container_width=True)
                    
                    csv_buffer = io.StringIO()
                    pairs_df.to_csv(csv_buffer, index=False)
                    
                    st.download_button(
                        label="📥 Download Pairs Analysis Data (CSV)",
                        data=csv_buffer.getvalue(),
                        file_name=f"{market}_pairs_analysis_window{selected_window_export}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.warning("No pairs data found for the selected window and strategies")
        else:
            st.info("No trading windows available for pairs export")

        st.markdown("---")
        
        # Analysis guidance
        st.subheader("📚 Analysis Guidance")
        
        with st.expander("🧮 Statistical Analysis Recommendations"):
            st.markdown("""
            **With the exported data, you can perform the following analyses:**
            
            **1. Significance Testing**
            ```python
            # Example: t-test for comparing daily returns
            from scipy import stats
            
            strategy1_returns = data[data['strategy'] == 'Strategy1']['daily_return']
            strategy2_returns = data[data['strategy'] == 'Strategy2']['daily_return']
            
            t_stat, p_value = stats.ttest_ind(strategy1_returns, strategy2_returns)
            ```
            
            **2. Consistency Analysis**
            ```python
            # Count how often Strategy A outperformed Strategy B
            comparison = data.pivot(index='date', columns='strategy', values='total_capital')
            strategy_a_wins = (comparison['StrategyA'] > comparison['StrategyB']).sum()
            ```
            
            **3. Risk-Adjusted Performance**
            ```python
            # Calculate Sharpe ratio, Sortino ratio, etc.
            risk_free_rate = 0.02  # from your trading parameters
            excess_returns = daily_returns - risk_free_rate/252
            sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
            ```
            
            **4. Transaction Cost Impact**
            ```python
            # Compare performance before and after costs
            gross_performance = net_performance + total_costs
            cost_impact = total_costs / initial_capital
            ```
            """)
        
        with st.expander("📋 Data Dictionary"):
            st.markdown("""
            **Performance Summary Fields:**
            - `strategy`: Strategy identifier
            - `total_trades`: Number of trades executed
            - `win_rate`: Percentage of profitable trades
            - `sharpe_ratio`: Risk-adjusted return measure
            - `max_drawdown`: Maximum peak-to-trough decline
            - `total_performance`: Net performance after costs
            - `total_costs`: Sum of all transaction costs
            
            **Timeseries Fields:**
            - `date`: Trading date
            - `total_capital`: Portfolio value
            - `daily_pnl`: Daily profit/loss
            - `cumulative_pnl`: Cumulative profit/loss
            - `active_positions`: Number of active positions
            
            **Pairs Analysis Fields:**
            - `pair_name`: Symbol pair identifier
            - `trades_in_window`: Number of trades for this pair
            - `total_performance`: Pair's contribution to portfolio
            - `win_rate`: Success rate for this pair
            """)