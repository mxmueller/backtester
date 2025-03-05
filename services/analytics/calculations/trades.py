import pandas as pd
from typing import Dict, List, Optional
from config import trading_config
from .portfolio import calculate_trade_performance_timeseries, calculate_performance_metrics


def get_trades_for_symbol(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    # Select only the symbol's trades
    symbol_trades = df[df['symbol'] == symbol].copy()

    # Explicitly select only needed columns
    essential_columns = ['symbol', 'entry_date', 'entry_price', 'exit_date',
                         'exit_price', 'position_type', 'paired_symbol']

    # Keep only essential columns that exist in the dataframe
    existing_columns = [col for col in essential_columns if col in symbol_trades.columns]
    symbol_trades = symbol_trades[existing_columns]

    # Calculate performance
    symbol_trades['performance'] = symbol_trades.apply(lambda x:
                                                       (x['exit_price'] - x['entry_price']) / x['entry_price'] if x[
                                                                                                                      'position_type'] == 'long'
                                                       else (x['entry_price'] - x['exit_price']) / x['entry_price'],
                                                       axis=1)

    # Always set exit_type based on performance (matching original behavior)
    symbol_trades['exit_type'] = symbol_trades['performance'].apply(lambda x:
                                                                    'profit' if x > 0 else (
                                                                        'break-even' if x == 0 else 'loss'))

    return symbol_trades


def get_symbol_performance(df: pd.DataFrame, symbol: str, window: Optional[int] = None,
                           config: Optional[Dict] = None) -> Dict:
    # Create a copy of the dataframe
    df_copy = df.copy()

    # Select only required columns for portfolio calculations
    required_columns = ['symbol', 'entry_date', 'entry_price', 'exit_date',
                        'exit_price', 'position_type']

    # Add window if it's needed for filtering
    if window is not None and 'window' in df_copy.columns:
        required_columns.append('window')

    # Keep only columns that exist in the dataframe
    existing_columns = [col for col in required_columns if col in df_copy.columns]
    df_copy = df_copy[existing_columns]

    # Apply filters
    symbol_filter = df_copy['symbol'] == symbol
    if window is not None and 'window' in df_copy.columns:
        symbol_filter &= (df_copy['window'] == window)

    symbol_trades = df_copy[symbol_filter]
    if symbol_trades.empty:
        return {}

    ts_data, trade_performances, trade_costs = calculate_trade_performance_timeseries(symbol_trades, config)
    return calculate_performance_metrics(ts_data, trade_performances, trade_costs, config)