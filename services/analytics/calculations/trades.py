import pandas as pd
from typing import Dict, List
from config import trading_config
from .portfolio import calculate_trade_performance_timeseries, calculate_performance_metrics

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

def get_symbol_performance(df: pd.DataFrame, symbol: str, window: int = None) -> Dict:
    symbol_filter = df['symbol'] == symbol
    if window is not None:
        symbol_filter &= (df['window'] == window)

    symbol_trades = df[symbol_filter].copy()
    if symbol_trades.empty:
        return {}

    ts_data, trade_performances, trade_costs = calculate_trade_performance_timeseries(symbol_trades)
    return calculate_performance_metrics(ts_data, trade_performances, trade_costs)