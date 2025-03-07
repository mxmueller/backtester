import streamlit as st
import pandas as pd
import plotly.express as px
from api import APIClient
from config import Config


def render(api_client: APIClient, config: Config):
    st.header("Market Overview")
    market = config.get_market()

    # Main layout - two columns for entire page
    left_col, right_col = st.columns([3, 2])

    # Left column - Market Index
    with left_col:
        st.subheader("Market Index")
        index_data = api_client.get_market_index(market)

        if not index_data:
            st.warning("Failed to fetch index data")
        else:
            df_index = pd.DataFrame([
                {'date': date, 'index_value': data['index']}
                for date, data in index_data.items()
            ])

            if df_index.empty:
                st.warning("No index data available")
            else:
                df_index['date'] = pd.to_datetime(df_index['date'])
                df_index = df_index.sort_values('date')

                # Compact metrics row
                current = df_index['index_value'].iloc[-1]
                change = current - df_index['index_value'].iloc[0]
                st.metric("Current", f"{current:.2f}", f"{change:.2f}")

                # Compact chart
                fig = px.line(df_index, x='date', y='index_value')
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
                fig.update_traces(line=dict(width=2))
                st.plotly_chart(fig, use_container_width=True)

        # Symbol comparison (moved below index in same column)
        symbols = config.get_symbols()
        selected_symbols = []

        if symbols:
            st.subheader("Symbol Comparison")
            selected_symbols = st.multiselect(
                "Compare symbols",
                symbols,
                max_selections=5
            )

            if selected_symbols:
                timeseries_data = {}
                for symbol in selected_symbols:
                    symbol_data = api_client.get_timeseries(market, symbol)
                    if symbol_data:
                        timeseries_data[symbol] = pd.DataFrame([
                            {'date': date, 'close': data['close'], 'symbol': symbol}
                            for date, data in symbol_data.items()
                        ])

                if timeseries_data:
                    combined_df = pd.concat(timeseries_data.values())
                    combined_df['date'] = pd.to_datetime(combined_df['date'])
                    combined_df = combined_df.sort_values('date')

                    fig = px.line(combined_df, x='date', y='close', color='symbol')
                    fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No data available for selected symbols")

    # Right column - Symbols list
    with right_col:
        st.subheader("Symbols")

        if not symbols:
            st.warning("No symbols available")
        else:
            st.text(f"Total: {len(symbols)}")

            # Compact symbol display
            symbols_df = pd.DataFrame({'Symbol': symbols})
            st.dataframe(
                symbols_df,
                use_container_width=True,
                height=560,
                hide_index=True
            )