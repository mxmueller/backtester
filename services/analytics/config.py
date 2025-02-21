minio_config = {
    "endpoint": "localhost:9000",
    "access_key": "minioadmin",
    "secret_key": "minioadmin",
    "secure": False
}

market_files = {
    "ftse100": {
        "bucket": "market-data",
        "file": "ftse_daily.parquet"
    }
}

trade_files = {
    "ftse100": {
        "bucket": "trading-data",
        "file": "ftse_trades.parquet"
    }
}

trading_config = {
    "initial_capital": 100000,
    "position_size_percent": 0.01,
    "fixed_commission": 1.0,
    "variable_fee": 0.00018,
    "bid_ask_spread": 0.001,
}