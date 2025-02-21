from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from data import MarketData, TradeData
from calculations import index, market, trades, portfolio, pairs
from calculations.symbol import get_symbol_timeseries
from config import market_files, trade_files

app = FastAPI(
    title="Stock Data API",
    description="API for retrieving stock data from Parquet files",
    version="1.0.0",
    openapi_tags=[
        {"name": "General", "description": "Basic endpoints"},
        {"name": "Markets", "description": "Market operations"},
        {"name": "Symbols", "description": "Symbol operations"},
        {"name": "Timeseries", "description": "Timeseries data"},
        {"name": "Index", "description": "Market index operations"},
        {"name": "Trades", "description": "Trade operations"}
    ]
)

market_data = MarketData(market_files)
trade_data = TradeData(trade_files)


@app.get("/api/markets", tags=["Markets"])
async def get_markets():
    return {"markets": market_data.get_markets()}


@app.get("/api/markets/{market_name}/symbols", tags=["Symbols"])
async def get_symbols_for_market(market_name: str):
    df = market_data.get_market_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market not found")
    return {"symbols": market.get_market_symbols(df)}


@app.get("/api/markets/{market_name}/timeseries/{symbol}", tags=["Timeseries"])
async def get_timeseries(market_name: str, symbol: str):
    df = market_data.get_market_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market not found")

    timeseries_data = get_symbol_timeseries(df, symbol)
    if not timeseries_data:
        raise HTTPException(status_code=404, detail="Symbol not found in this market")
    return timeseries_data


@app.get("/api/markets/{market_name}/index", tags=["Index"])
async def get_market_index(market_name: str):
    df = market_data.get_market_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market not found")
    return index.calculate_market_index(df)


@app.get("/api/markets/{market_name}/trades/performance", tags=["Trades"])
async def get_trades_performance(market_name: str):
    df = trade_data.get_trade_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market trades not found")
    ts_data, trade_performances, trade_costs = portfolio.calculate_trade_performance_timeseries(df)
    return portfolio.calculate_performance_metrics(ts_data, trade_performances, trade_costs)


@app.get("/api/markets/{market_name}/trades/performance/timeseries", tags=["Trades"])
async def get_trades_performance_timeseries(market_name: str):
    df = trade_data.get_trade_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market trades not found")
    ts_data, _, _ = portfolio.calculate_trade_performance_timeseries(df)
    return {"timeseries": ts_data.to_dict('index')}


@app.get("/api/markets/{market_name}/trades/{symbol}", tags=["Trades"])
async def get_symbol_trades(market_name: str, symbol: str):
    df = trade_data.get_trade_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market trades not found")

    symbol_trades = trades.get_trades_for_symbol(df, symbol)
    if len(symbol_trades) == 0:
        raise HTTPException(status_code=404, detail="No trades found for this symbol")
    return symbol_trades.to_dict('records')


@app.get("/api/markets/{market_name}/trades/{symbol}/performance", tags=["Trades"])
async def get_symbol_performance(market_name: str, symbol: str, window: int = None):
    df = trade_data.get_trade_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market trades not found")

    performance = trades.get_symbol_performance(df, symbol, window)
    if not performance:
        raise HTTPException(status_code=404, detail="No trades found for this symbol")
    return performance


@app.get("/api/markets/{market_name}/pairs/windows", tags=["Pairs"])
async def get_available_windows(market_name: str):
    df = trade_data.get_trade_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market trades not found")

    windows = df['window'].unique().tolist()
    return {"windows": sorted(windows)}


@app.get("/api/markets/{market_name}/pairs/window/{window}", tags=["Pairs"])
async def get_pairs_for_window(market_name: str, window: int):
    df = trade_data.get_trade_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market trades not found")

    return pairs.get_pairs_by_window(df, window)


@app.get("/api/markets/{market_name}/pairs/{symbol1}/{symbol2}/performance", tags=["Pairs"])
async def get_pair_performance(market_name: str, symbol1: str, symbol2: str, window: int = None):
    df = trade_data.get_trade_data(market_name)
    if df is None:
        raise HTTPException(status_code=404, detail="Market trades not found")

    performance = pairs.get_pair_performance(df, symbol1, symbol2, window)
    if not performance:
        raise HTTPException(status_code=404, detail="No trades found for this pair")

    return performance