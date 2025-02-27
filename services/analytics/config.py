from fastapi import HTTPException
from typing import Dict, Optional

minio_config = {
    "endpoint": "localhost:9000",
    "access_key": "minioadmin",
    "secret_key": "minioadmin",
    "secure": False
}

base_bucket = "markets"

markets = {
    "FTSE100": {
        "market_data": "market_data.parquet",
        "strategies_path": "strategies"
    },
    "NASDAQ100": {
        "market_data": "market_data.parquet",
        "strategies_path": "strategies"
    }
}

trading_config = {
    "initial_capital": 100000,
    "position_size_percent": 0.01,
    "fixed_commission": 1.0,
    "variable_fee": 0.00018,
    "bid_ask_spread": 0.001,
    "risk_free_rate": 0.00
}

def validate_trading_params(params: Dict[str, float]) -> None:
    if 'initial_capital' in params and params['initial_capital'] <= 0:
        raise HTTPException(status_code=400, detail="initial_capital must be > 0")
    if 'position_size_percent' in params and not 0 < params['position_size_percent'] < 1:
        raise HTTPException(status_code=400, detail="position_size_percent must be between 0 and 1")
    if 'fixed_commission' in params and params['fixed_commission'] < 0:
        raise HTTPException(status_code=400, detail="fixed_commission must be >= 0")
    if 'variable_fee' in params and params['variable_fee'] < 0:
        raise HTTPException(status_code=400, detail="variable_fee must be >= 0")
    if 'bid_ask_spread' in params and params['bid_ask_spread'] < 0:
        raise HTTPException(status_code=400, detail="bid_ask_spread must be >= 0")
    if 'risk_free_rate' in params and params['risk_free_rate'] < 0:
        raise HTTPException(status_code=400, detail="risk_free_rate must be >= 0")

def get_trading_config(
    initial_capital: Optional[float] = None,
    position_size_percent: Optional[float] = None,
    fixed_commission: Optional[float] = None,
    variable_fee: Optional[float] = None,
    bid_ask_spread: Optional[float] = None,
    risk_free_rate: Optional[float] = None
) -> Dict[str, float]:
    custom_config = {k: v for k, v in locals().items() if v is not None and k in trading_config}
    validate_trading_params(custom_config)
    return {**trading_config, **custom_config}

def get_market_path(market_name: str) -> str:
    market_upper = market_name.upper()
    if market_upper not in markets:
        raise HTTPException(status_code=404, detail="Market not found")
    return f"{base_bucket}/{market_upper}"

def get_strategies_path(market_name: str) -> str:
    return f"{get_market_path(market_name)}/{markets[market_name.upper()]['strategies_path']}"