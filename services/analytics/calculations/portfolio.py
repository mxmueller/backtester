import pandas as pd
from typing import Dict, Tuple, List
from config import trading_config

def calculate_trading_costs(position_size: float, exit_value: float, config: Dict) -> Tuple[float, float]:
    entry_costs = (
            config['fixed_commission'] +
            position_size * config['variable_fee'] +
            position_size * (config['bid_ask_spread'])
    )
    exit_costs = (
            config['fixed_commission'] +
            exit_value * config['variable_fee'] +
            exit_value * (config['bid_ask_spread'])
    )
    return entry_costs, exit_costs

def _calculate_metrics(performance_series: pd.Series) -> Dict:
    return {
        'total_trades': len(performance_series),
        'profitable_trades': len(performance_series[performance_series > 0]),
        'total_performance': performance_series.sum(),
        'avg_performance': performance_series.mean(),
        'max_gain': performance_series.max(),
        'max_loss': performance_series.min(),
        'win_rate': len(performance_series[performance_series > 0]) / len(performance_series)
    }

def calculate_trade_performance_timeseries(df: pd.DataFrame, config: Dict = None) -> Tuple[pd.DataFrame, List[Dict], List[Dict]]:
    if config is None:
        config = trading_config

    df = df.sort_values(['entry_date', 'exit_date'])
    date_range = pd.date_range(df['entry_date'].min(), df['exit_date'].max(), freq='D')

    ts_data = pd.DataFrame(index=date_range)
    available_capital = config['initial_capital']
    invested_capital = 0
    active_positions = {}
    daily_costs = pd.Series(0, index=date_range)
    skipped_trades = []
    trade_performances = []
    trade_costs = []

    for date in date_range:
        new_trades = df[df['entry_date'].dt.date == date.date()]
        closed_trades = df[df['exit_date'].dt.date == date.date()]

        daily_entry_costs = 0
        daily_exit_costs = 0
        daily_pnl = 0

        for idx, trade in new_trades.iterrows():
            position_size = min(available_capital * config['position_size_percent'], available_capital)
            if position_size <= 0:
                skipped_trades.append(idx)
                continue

            units = position_size / trade['entry_price']
            entry_costs, _ = calculate_trading_costs(position_size, 0, config)

            if entry_costs >= available_capital:
                skipped_trades.append(idx)
                continue

            available_capital -= (position_size + entry_costs)
            invested_capital += position_size
            daily_entry_costs += entry_costs

            active_positions[idx] = {
                'units': units,
                'position_size': position_size,
                'entry_price': trade['entry_price'],
                'position_type': trade['position_type'],
                'entry_costs': {
                    'commission': config['fixed_commission'],
                    'variable': position_size * config['variable_fee'],
                    'spread': position_size * config['bid_ask_spread']
                }
            }

        for idx, trade in closed_trades.iterrows():
            if idx not in active_positions:
                continue

            pos = active_positions[idx]
            exit_value = pos['units'] * trade['exit_price']
            _, exit_costs = calculate_trading_costs(pos['position_size'], exit_value, config)

            pnl = ((trade['exit_price'] - pos['entry_price']) * pos['units']
                   if pos['position_type'] == 'long'
                   else (pos['entry_price'] - trade['exit_price']) * pos['units'])

            raw_performance = (
                (trade['exit_price'] - pos['entry_price']) / pos['entry_price']
                if pos['position_type'] == 'long'
                else (pos['entry_price'] - trade['exit_price']) / pos['entry_price']
            )

            exit_cost_breakdown = {
                'commission': config['fixed_commission'],
                'variable': exit_value * config['variable_fee'],
                'spread': exit_value * config['bid_ask_spread']
            }

            total_costs = sum(pos['entry_costs'].values()) + sum(exit_cost_breakdown.values())
            cost_impact = total_costs / (config['initial_capital'] * config['position_size_percent'])

            trade_performances.append({
                'trade_id': idx,
                'raw_performance': raw_performance,
                'cost_impact': cost_impact,
                'net_performance': raw_performance - cost_impact
            })

            trade_costs.append({
                'trade_id': idx,
                'entry': pos['entry_costs'],
                'exit': exit_cost_breakdown,
                'total': total_costs
            })

            invested_capital -= pos['position_size']
            available_capital += (pos['position_size'] + pnl - exit_costs)
            daily_exit_costs += exit_costs
            daily_pnl += pnl
            del active_positions[idx]

        daily_costs[date] = daily_entry_costs + daily_exit_costs

        ts_data.loc[date, 'available_capital'] = available_capital
        ts_data.loc[date, 'invested_capital'] = invested_capital
        ts_data.loc[date, 'total_capital'] = available_capital + invested_capital
        ts_data.loc[date, 'daily_pnl'] = daily_pnl
        ts_data.loc[date, 'daily_costs'] = daily_costs[date]
        ts_data.loc[date, 'active_positions'] = len(active_positions)

    ts_data['cumulative_pnl'] = ts_data['daily_pnl'].cumsum()
    ts_data['cumulative_costs'] = daily_costs.cumsum()
    ts_data['net_performance'] = ts_data['cumulative_pnl'] - ts_data['cumulative_costs']
    ts_data['performance_pct'] = ts_data['net_performance'] / config['initial_capital']

    return ts_data, trade_performances, trade_costs

def calculate_performance_metrics(ts_data: pd.DataFrame, trade_performances: List[Dict],
                               trade_costs: List[Dict], config: Dict = None) -> Dict:
    if config is None:
        config = trading_config

    raw_performance_series = pd.Series([t['raw_performance'] for t in trade_performances])
    cost_impact_series = pd.Series([t['cost_impact'] for t in trade_performances])
    net_performance_series = pd.Series([t['net_performance'] for t in trade_performances])

    entry_breakdown = {
        'commission': sum(t['entry']['commission'] for t in trade_costs),
        'variable': sum(t['entry']['variable'] for t in trade_costs),
        'spread': sum(t['entry']['spread'] for t in trade_costs)
    }
    entry_breakdown['total'] = sum(entry_breakdown.values())

    exit_breakdown = {
        'commission': sum(t['exit']['commission'] for t in trade_costs),
        'variable': sum(t['exit']['variable'] for t in trade_costs),
        'spread': sum(t['exit']['spread'] for t in trade_costs)
    }
    exit_breakdown['total'] = sum(exit_breakdown.values())

    executed_trades = len(trade_performances)
    total_costs = ts_data['cumulative_costs'].iloc[-1]

    return {
        'total_trades': executed_trades,
        'profitable_days': len(ts_data[ts_data['daily_pnl'] > 0]),
        'total_days': len(ts_data),
        'max_invested': ts_data['invested_capital'].max(),
        'total_costs': total_costs,
        'final_performance': ts_data['performance_pct'].iloc[-1],
        'max_drawdown': (ts_data['total_capital'].min() - config['initial_capital']) / config['initial_capital'],
        'raw_performance': _calculate_metrics(raw_performance_series),
        'net_performance': _calculate_metrics(net_performance_series),
        'costs': {
            'total_costs': total_costs,
            'avg_cost_per_trade': total_costs / executed_trades,
            'breakdown': {
                'entry': entry_breakdown,
                'exit': exit_breakdown
            }
        },
        'portfolio': {
            'initial_capital': config['initial_capital'],
            'final_capital': ts_data['total_capital'].iloc[-1],
            'max_capital': ts_data['total_capital'].max(),
            'min_capital': ts_data['total_capital'].min(),
            'current_invested': ts_data['invested_capital'].iloc[-1],
            'current_available': ts_data['available_capital'].iloc[-1]
        }
    }