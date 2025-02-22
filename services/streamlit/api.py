import httpx
from typing import Dict, Optional, List


class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def get_markets(self) -> List[str]:
        response = await self.client.get(f"{self.base_url}/api/markets")
        return response.json()["markets"]

    async def get_performance_timeseries(
            self,
            market: str,
            trading_params: Optional[Dict] = None
    ) -> Dict:
        params = trading_params or {}
        response = await self.client.get(
            f"{self.base_url}/api/markets/{market}/trades/performance/timeseries",
            params=params
        )
        return response.json()["timeseries"]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()