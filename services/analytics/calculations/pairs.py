import pandas as pd
from typing import Dict, List, Optional
from .portfolio import calculate_trade_performance_timeseries, calculate_performance_metrics

def get_pairs_by_window(df: pd.DataFrame, window: int = None) -> Dict:
    df = df.sort_values(['window', 'entry_date'])
    windows = [window] if window is not None else df['window'].unique().tolist()
    result = {}

    for w in windows:
        window_trades = df[df['window'] == w]
        pairs_dict = {}

        for _, row in window_trades.iterrows():
            pair = tuple(sorted([row['symbol'], row['paired_symbol']]))
            if pair not in pairs_dict:
                pairs_dict[pair] = 0
            pairs_dict[pair] += 1

        pairs_list = [{"pair": list(k), "trades": v} for k, v in pairs_dict.items()]

        result[int(w)] = {
            "pairs": pairs_list,
            "total_pairs": len(pairs_list),
            "total_trades": sum(p["trades"] for p in pairs_list)
        }

    return result

def get_pair_performance(df: pd.DataFrame, symbol1: str, symbol2: str, window: Optional[int] = None, config: Optional[Dict] = None) -> Dict:
    pair_filter = ((df['symbol'] == symbol1) & (df['paired_symbol'] == symbol2)) | \
                  ((df['symbol'] == symbol2) & (df['paired_symbol'] == symbol1))

    if window is not None:
        pair_filter &= (df['window'] == window)

    pair_trades = df[pair_filter].copy()
    if pair_trades.empty:
        return {}

    ts_data, trade_performances, trade_costs = calculate_trade_performance_timeseries(pair_trades, config)
    return calculate_performance_metrics(ts_data, trade_performances, trade_costs, config)