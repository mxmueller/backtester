# trades.py
import pandas as pd
from typing import Dict, List
from config import trading_config

def get_trades_for_symbol(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    symbol_trades = df[df['symbol'] == symbol].copy()
    columns_to_drop = ['window', 'trade_id']
    symbol_trades.drop(columns=columns_to_drop, inplace=True, errors='ignore')
    symbol_trades['performance'] = symbol_trades.apply(lambda x:
        (x['exit_price'] - x['entry_price']) / x['entry_price'] if x['position_type'] == 'long'
        else (x['entry_price'] - x['exit_price']) / x['entry_price'], axis=1)
    symbol_trades['exit_type'] = symbol_trades['performance'].apply(lambda x:
        'profit' if x > 0 else ('break-even' if x == 0 else 'loss'))
    return symbol_trades