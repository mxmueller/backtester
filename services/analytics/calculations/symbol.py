import pandas as pd
from typing import Dict

def get_symbol_timeseries(df: pd.DataFrame, symbol: str) -> Dict:
    symbol_data = df[df['symbol'] == symbol]
    symbol_data.index = symbol_data.index.strftime('%Y-%m-%d')
    return symbol_data.to_dict('index')