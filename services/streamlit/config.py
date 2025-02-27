from typing import Dict, Any, Optional, List
from api import APIClient

class Config:
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self.market = None
        self.strategy = None
        self.trading_params = {
            "initial_capital": 100000.0,
            "position_size_percent": 0.01,
            "fixed_commission": 1.0,
            "variable_fee": 0.00018,
            "bid_ask_spread": 0.001,
            "risk_free_rate": 0.0
        }
        self.symbols = []
        self.windows = []

    def set_market(self, market: str) -> None:
        if market != self.market:
            self.market = market
            self._update_symbols()

    def set_strategy(self, strategy: str) -> None:
        if strategy != self.strategy:
            self.strategy = strategy
            self._update_windows()

    def set_trading_params(self, params: Dict[str, float]) -> None:
        self.trading_params = params

    def _update_symbols(self) -> None:
        if self.market:
            symbols_data = self.api_client.get_symbols_for_market(self.market)
            self.symbols = symbols_data.get("symbols", [])
        else:
            self.symbols = []

    def _update_windows(self) -> None:
        if self.market and self.strategy:
            windows_data = self.api_client.get_available_windows(self.market, self.strategy)
            self.windows = windows_data.get("windows", [])
        else:
            self.windows = []

    def get_market(self) -> Optional[str]:
        return self.market

    def get_strategy(self) -> Optional[str]:
        return self.strategy

    def get_trading_params(self) -> Dict[str, float]:
        return self.trading_params

    def get_symbols(self) -> List[str]:
        return self.symbols

    def get_windows(self) -> List[int]:
        return self.windows