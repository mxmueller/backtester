import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from api import APIClient
from config import Config


def render(api_client: APIClient, config: Config):
    st.header("Market Overview")

    market = config.get_market()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Market Index")
        index_data = api_client.get_market_index(market)

        if index_data:
            df_index = pd.DataFrame([
                {
                    'date': date,
                    'index_value': data['index']
                }
                for date, data in index_data.items()
            ])

            if not df_index.empty:
                df_index['date'] = pd.to_datetime(df_index['date'])
                df_index = df_index.sort_values('date')

                fig = px.line(
                    df_index,
                    x='date',
                    y='index_value',
                    title=f"{market} Index"
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

                st.metric(
                    "Index Change",
                    f"{df_index['index_value'].iloc[-1]:.2f}",
                    f"{df_index['index_value'].iloc[-1] - df_index['index_value'].iloc[0]:.2f}"
                )
            else:
                st.warning("No index data available")
        else:
            st.warning("Failed to fetch index data")

    with col2:
        st.subheader("Symbols")
        symbols = config.get_symbols()

        if symbols:
            st.write(f"Total symbols: {len(symbols)}")

            symbols_df = pd.DataFrame({'Symbol': symbols})
            st.dataframe(symbols_df, use_container_width=True)

            selected_symbols = st.multiselect(
                "Select symbols to compare",
                symbols,
                max_selections=5
            )

            if selected_symbols:
                timeseries_data = {}

                for symbol in selected_symbols:
                    symbol_data = api_client.get_timeseries(market, symbol)

                    if symbol_data:
                        timeseries_data[symbol] = pd.DataFrame([
                            {
                                'date': date,
                                'close': data['close'],
                                'symbol': symbol
                            }
                            for date, data in symbol_data.items()
                        ])

                if timeseries_data:
                    combined_df = pd.concat(timeseries_data.values())
                    combined_df['date'] = pd.to_datetime(combined_df['date'])
                    combined_df = combined_df.sort_values('date')

                    fig = px.line(
                        combined_df,
                        x='date',
                        y='close',
                        color='symbol',
                        title="Symbol Price Comparison"
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No data available for selected symbols")
        else:
            st.warning("No symbols available")