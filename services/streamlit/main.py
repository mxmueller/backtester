import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import numpy as np

st.set_page_config(layout="wide")

API_URL = 'http://127.0.0.1:8000/api'

try:
    response_markets = requests.get(API_URL + '/markets')
    response_markets.raise_for_status()
    available_markets = response_markets.json().get('markets', [])
except requests.exceptions.RequestException as e:
    st.error(f"Error connecting to API for markets: {e}")
    available_markets = []

if not available_markets:
    st.stop()

selected_market = st.selectbox('Choose a Market:', available_markets)

if not selected_market:
    st.stop()

tab1, tab2 = st.tabs(["Market Analysis", "Pairs Analysis"])

with tab1:
    try:
        response_index = requests.get(API_URL + f'/markets/{selected_market}/index')
        response_index.raise_for_status()
        index_data = response_index.json()

        if not index_data:
            st.warning(f"No index data returned for {selected_market}")
            st.stop()

        df_index = pd.DataFrame.from_dict(index_data, orient='index')

        fig_index = px.line(df_index, x=df_index.index, y='index', title=f"{selected_market} Market Index")
        fig_index.update_xaxes(
            title_text="Year",
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1d", step="day", stepmode="backward"),
                    dict(count=7, label="1w", step="day", stepmode="backward"),
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            )
        )
        st.plotly_chart(fig_index)

        response_symbols = requests.get(API_URL + f'/markets/{selected_market}/symbols')
        response_symbols.raise_for_status()
        available_symbols = response_symbols.json().get('symbols', [])

        if not available_symbols:
            st.warning(f"No symbols returned for {selected_market}")
            st.stop()

        selected_symbol = st.selectbox(f'Choose a Stock:', available_symbols)

        if selected_symbol:
            response_symbol_data = requests.get(API_URL + f'/markets/{selected_market}/timeseries/{selected_symbol}')
            response_symbol_data.raise_for_status()
            symbol_data = response_symbol_data.json()

            if symbol_data:
                df_symbol = pd.DataFrame.from_dict(symbol_data, orient='index')
                fig_symbol = px.line(df_symbol, x=df_symbol.index, y='close', title=f"{selected_symbol} Timeseries")
                fig_symbol.update_xaxes(
                    title_text="Year",
                    rangeselector=dict(
                        buttons=list([
                            dict(count=1, label="1d", step="day", stepmode="backward"),
                            dict(count=7, label="1w", step="day", stepmode="backward"),
                            dict(count=1, label="1m", step="month", stepmode="backward"),
                            dict(count=6, label="6m", step="month", stepmode="backward"),
                            dict(count=1, label="1y", step="year", stepmode="backward"),
                            dict(step="all")
                        ])
                    )
                )
                st.plotly_chart(fig_symbol)

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")

with tab2:
    st.header("Pairs Analysis")

    try:
        response_windows = requests.get(API_URL + f'/markets/{selected_market}/pairs/windows')
        response_windows.raise_for_status()
        available_windows = response_windows.json()


        col1, col2 = st.columns([1, 2])

        with col1:
            # Corrected line: Use available_windows['windows'] to get the list
            selected_window = st.selectbox("Select Window Size:", available_windows['windows'])

            if selected_window:
                response_pairs = requests.get(API_URL + f'/markets/{selected_market}/pairs/window/{selected_window}')
                response_pairs.raise_for_status()
                pairs_data = response_pairs.json().get(str(selected_window), {})

                if pairs_data:
                    st.metric("Total Pairs", pairs_data["total_pairs"])
                    st.metric("Total Trades", pairs_data["total_trades"])

                    pairs_list = pairs_data.get("pairs", [])

                    G = nx.Graph()
                    edge_weights = []

                    for pair_info in pairs_list:
                        stock1, stock2 = pair_info["pair"]
                        trades = pair_info["trades"]
                        G.add_edge(stock1, stock2, weight=trades)
                        edge_weights.append(trades)

                    pos = nx.spring_layout(G)

                    edge_trace = go.Scatter(
                        x=[], y=[], line=dict(width=0.5, color='#888'), hoverinfo='none', mode='lines')

                    for edge in G.edges():
                        x0, y0 = pos[edge[0]]
                        x1, y1 = pos[edge[1]]
                        edge_trace['x'] += tuple([x0, x1, None])
                        edge_trace['y'] += tuple([y0, y1, None])

                    node_trace = go.Scatter(
                        x=[], y=[], text=[], mode='markers+text', hoverinfo='text',
                        marker=dict(size=20, line_width=2))

                    for node in G.nodes():
                        x, y = pos[node]
                        node_trace['x'] += tuple([x])
                        node_trace['y'] += tuple([y])
                        node_trace['text'] += tuple([node])

                    fig = go.Figure(data=[edge_trace, node_trace],
                                    layout=go.Layout(
                                        showlegend=False,
                                        hovermode='closest',
                                        margin=dict(b=20, l=5, r=5, t=40),
                                        title=f"Pairs Network - Window {selected_window}",
                                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                                    )

                    with col2:
                        st.plotly_chart(fig, use_container_width=True)

                    st.subheader("Pairs Details")
                    df_pairs = pd.DataFrame(pairs_list)
                    df_pairs['pair'] = df_pairs['pair'].apply(lambda x: ' - '.join(x))
                    st.dataframe(df_pairs.sort_values('trades', ascending=False))

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching pairs data: {e}")