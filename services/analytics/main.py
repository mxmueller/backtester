from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from data import MarketData, TradeData
from calculations import index, market, trades, portfolio, pairs
from calculations.symbol import get_symbol_timeseries
from config import get_trading_config
from typing import Optional

app = FastAPI(
    title="Stock Data API",
    description="API for retrieving stock data and trading strategies",
    version="1.0.0",
    openapi_tags=[
        {"name": "Markets", "description": "Market operations"},
        {"name": "Strategies", "description": "Strategy operations"},
        {"name": "Symbols", "description": "Symbol operations"},
        {"name": "Timeseries", "description": "Timeseries data"},
        {"name": "Index", "description": "Market index operations"},
        {"name": "Trades", "description": "Trade operations"}
    ]
)

market_data = MarketData()
trade_data = TradeData()


@app.get("/api/markets", tags=["Markets"])
async def get_markets():
    return {"markets": market_data.get_markets()}


@app.get("/api/markets/{market_name}/strategies", tags=["Strategies"])
async def get_market_strategies(market_name: str):
    try:
        strategies = trade_data.list_strategies(market_name)
        return {"strategies": strategies}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/markets/{market_name}/symbols", tags=["Symbols"])
async def get_symbols_for_market(market_name: str):
    df = market_data.get_market_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market not found")

    symbols = market.get_market_symbols(df)
    return {"symbols": symbols}


@app.get("/api/markets/{market_name}/timeseries/{symbol}", tags=["Timeseries"])
async def get_timeseries(market_name: str, symbol: str):
    df = market_data.get_market_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market not found")

    timeseries_data = get_symbol_timeseries(df, symbol)
    if not timeseries_data:
        raise HTTPException(status_code=404, detail="Symbol not found in market data")
    return timeseries_data


@app.get("/api/markets/{market_name}/index", tags=["Index"])
async def get_market_index(market_name: str):
    df = market_data.get_market_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market not found")

    return index.calculate_market_index(df)


@app.get("/api/markets/{market_name}/trades/performance", tags=["Trades"])
async def get_trades_performance(
        market_name: str,
        strategy_version: str = Query(..., description="Strategy version ID"),
        initial_capital: Optional[float] = None,
        position_size_percent: Optional[float] = None,
        fixed_commission: Optional[float] = None,
        variable_fee: Optional[float] = None,
        bid_ask_spread: Optional[float] = None,
        risk_free_rate: Optional[float] = None
):
    try:
        df = trade_data.load_strategy(market_name, strategy_version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {str(e)}")

    config = get_trading_config(
        initial_capital=initial_capital,
        position_size_percent=position_size_percent,
        fixed_commission=fixed_commission,
        variable_fee=variable_fee,
        bid_ask_spread=bid_ask_spread,
        risk_free_rate=risk_free_rate
    )

    ts_data, trade_performances, trade_costs = portfolio.calculate_trade_performance_timeseries(df, config)
    metrics = portfolio.calculate_performance_metrics(ts_data, trade_performances, trade_costs, config)

    strategy_metadata = trade_data.get_strategy_metadata(market_name, strategy_version)
    return {
        "performance": metrics,
        "strategy": {
            "version": strategy_version,
            "metadata": strategy_metadata
        }
    }


@app.get("/api/markets/{market_name}/trades/performance/timeseries", tags=["Trades"])
async def get_trades_performance_timeseries(
        market_name: str,
        strategy_version: str = Query(..., description="Strategy version ID"),
        initial_capital: Optional[float] = None,
        position_size_percent: Optional[float] = None,
        fixed_commission: Optional[float] = None,
        variable_fee: Optional[float] = None,
        bid_ask_spread: Optional[float] = None,
        risk_free_rate: Optional[float] = None
):
    try:
        df = trade_data.load_strategy(market_name, strategy_version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {str(e)}")

    config = get_trading_config(
        initial_capital=initial_capital,
        position_size_percent=position_size_percent,
        fixed_commission=fixed_commission,
        variable_fee=variable_fee,
        bid_ask_spread=bid_ask_spread,
        risk_free_rate=risk_free_rate
    )

    ts_data, _, _ = portfolio.calculate_trade_performance_timeseries(df, config)
    return {"timeseries": ts_data.to_dict('index')}


@app.get("/api/markets/{market_name}/trades/{symbol}", tags=["Trades"])
async def get_symbol_trades(
        market_name: str,
        symbol: str,
        strategy_version: str = Query(..., description="Strategy version ID")
):
    try:
        df = trade_data.load_strategy(market_name, strategy_version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {str(e)}")

    symbol_trades = trades.get_trades_for_symbol(df, symbol)
    if len(symbol_trades) == 0:
        raise HTTPException(status_code=404, detail="No trades found for this symbol")
    return symbol_trades.to_dict('records')


@app.get("/api/markets/{market_name}/trades/{symbol}/performance", tags=["Trades"])
async def get_symbol_performance(
        market_name: str,
        symbol: str,
        strategy_version: str = Query(..., description="Strategy version ID"),
        window: int = None,
        initial_capital: Optional[float] = None,
        position_size_percent: Optional[float] = None,
        fixed_commission: Optional[float] = None,
        variable_fee: Optional[float] = None,
        bid_ask_spread: Optional[float] = None,
        risk_free_rate: Optional[float] = None
):
    try:
        df = trade_data.load_strategy(market_name, strategy_version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {str(e)}")

    config = get_trading_config(
        initial_capital=initial_capital,
        position_size_percent=position_size_percent,
        fixed_commission=fixed_commission,
        variable_fee=variable_fee,
        bid_ask_spread=bid_ask_spread,
        risk_free_rate=risk_free_rate
    )

    performance = trades.get_symbol_performance(df, symbol, window, config)
    if not performance:
        raise HTTPException(status_code=404, detail="No trades found for this symbol")
    return performance


@app.get("/api/markets/{market_name}/pairs/windows", tags=["Pairs"])
async def get_available_windows(
        market_name: str,
        strategy_version: str = Query(..., description="Strategy version ID")
):
    try:
        df = trade_data.load_strategy(market_name, strategy_version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {str(e)}")

    windows = df['window'].unique().tolist()
    return {"windows": sorted(windows)}


@app.get("/api/markets/{market_name}/pairs/window/{window}", tags=["Pairs"])
async def get_pairs_for_window(
        market_name: str,
        window: int,
        strategy_version: str = Query(..., description="Strategy version ID")
):
    try:
        df = trade_data.load_strategy(market_name, strategy_version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {str(e)}")

    return pairs.get_pairs_by_window(df, window)


@app.get("/api/markets/{market_name}/pairs/{symbol1}/{symbol2}/performance", tags=["Pairs"])
async def get_pair_performance(
        market_name: str,
        symbol1: str,
        symbol2: str,
        strategy_version: str = Query(..., description="Strategy version ID"),
        window: int = None,
        initial_capital: Optional[float] = None,
        position_size_percent: Optional[float] = None,
        fixed_commission: Optional[float] = None,
        variable_fee: Optional[float] = None,
        bid_ask_spread: Optional[float] = None,
        risk_free_rate: Optional[float] = None
):
    try:
        df = trade_data.load_strategy(market_name, strategy_version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {str(e)}")

    config = get_trading_config(
        initial_capital=initial_capital,
        position_size_percent=position_size_percent,
        fixed_commission=fixed_commission,
        variable_fee=variable_fee,
        bid_ask_spread=bid_ask_spread,
        risk_free_rate=risk_free_rate
    )

    performance = pairs.get_pair_performance(df, symbol1, symbol2, window, config)
    if not performance:
        raise HTTPException(status_code=404, detail="No trades found for this pair")
    return performance