import pandas as pd
from typing import Dict, List


def calculate_market_index(df: pd.DataFrame) -> Dict[str, float]:
    df = df.sort_index()
    index_values = []
    initial_prices = df.groupby('symbol')['close'].first()

    for date in df.index.unique():
        current_prices = df.loc[date].groupby('symbol')['close'].first()
        daily_index = (current_prices / initial_prices).mean() * 100
        index_values.append(daily_index)

    index_df = pd.DataFrame(index=df.index.unique(), data={'index': index_values})
    index_df.index = index_df.index.strftime('%Y-%m-%d')
    return index_df.to_dict('index')