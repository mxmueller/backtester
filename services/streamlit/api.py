import requests
import json
from typing import Dict, Any, Optional, List, Union


class APIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            return None

    def get_markets(self) -> Dict[str, List[str]]:
        return self._make_request("/api/markets") or {"markets": []}

    def get_market_strategies(self, market_name: str) -> Dict[str, List[Dict[str, Any]]]:
        return self._make_request(f"/api/markets/{market_name}/strategies") or {"strategies": []}

    def get_symbols_for_market(self, market_name: str) -> Dict[str, List[str]]:
        return self._make_request(f"/api/markets/{market_name}/symbols") or {"symbols": []}

    def get_timeseries(self, market_name: str, symbol: str) -> Dict[str, Dict[str, Any]]:
        return self._make_request(f"/api/markets/{market_name}/timeseries/{symbol}") or {}

    def get_market_index(self, market_name: str) -> Dict[str, Dict[str, Any]]:
        return self._make_request(f"/api/markets/{market_name}/index") or {}

    def get_trades_performance(self, market_name: str, strategy_version: str, trading_params: Dict[str, float]) -> Dict[
        str, Any]:
        return self._make_request(f"/api/markets/{market_name}/trades/performance",
                                  {"strategy_version": strategy_version, **trading_params}) or {}

    def get_trades_performance_timeseries(self, market_name: str, strategy_version: str,
                                          trading_params: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        return self._make_request(f"/api/markets/{market_name}/trades/performance/timeseries",
                                  {"strategy_version": strategy_version, **trading_params}) or {"timeseries": {}}

    def get_symbol_trades(self, market_name: str, symbol: str, strategy_version: str) -> List[Dict[str, Any]]:
        return self._make_request(f"/api/markets/{market_name}/trades/{symbol}",
                                  {"strategy_version": strategy_version}) or []

    def get_symbol_performance(self, market_name: str, symbol: str, strategy_version: str, window: Optional[int] = None,
                               trading_params: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        params = {"strategy_version": strategy_version}
        if window is not None:
            params["window"] = window
        if trading_params:
            params.update(trading_params)
        return self._make_request(f"/api/markets/{market_name}/trades/{symbol}/performance", params) or {}

    def get_available_windows(self, market_name: str, strategy_version: str) -> Dict[str, List[int]]:
        return self._make_request(f"/api/markets/{market_name}/pairs/windows",
                                  {"strategy_version": strategy_version}) or {"windows": []}

    def get_pairs_for_window(self, market_name: str, window: int, strategy_version: str) -> Dict[str, Any]:
        return self._make_request(f"/api/markets/{market_name}/pairs/window/{window}",
                                  {"strategy_version": strategy_version}) or {}

    def get_pair_performance(self, market_name: str, symbol1: str, symbol2: str, strategy_version: str,
                             window: Optional[int] = None, trading_params: Optional[Dict[str, float]] = None) -> Dict[
        str, Any]:
        params = {"strategy_version": strategy_version}
        if window is not None:
            params["window"] = window
        if trading_params:
            params.update(trading_params)
        return self._make_request(f"/api/markets/{market_name}/pairs/{symbol1}/{symbol2}/performance", params) or {}