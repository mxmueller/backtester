import pandas as pd
import pyarrow.parquet as pq
import io
from minio import Minio
from typing import Dict, Any
from config import minio_config

class MinioClient:
    def __init__(self):
        self.client = Minio(
            minio_config["endpoint"],
            access_key=minio_config["access_key"],
            secret_key=minio_config["secret_key"],
            secure=minio_config["secure"]
        )

    def get_object(self, bucket: str, file_path: str) -> bytes:
        try:
            data = self.client.get_object(bucket, file_path)
            return data.read()
        except Exception as e:
            print(f"Error reading from MinIO: {e}")
            exit()

class MarketData:
    def __init__(self, market_files: Dict[str, Dict[str, str]]):
        self.market_data = {}
        self.minio = MinioClient()
        self.load_markets(market_files)

    def load_markets(self, market_files: Dict[str, Dict[str, str]]) -> None:
        for market_name, file_info in market_files.items():
            data = self.minio.get_object(file_info["bucket"], file_info["file"])
            df = pd.read_parquet(io.BytesIO(data))
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            self.market_data[market_name] = df

    def get_market_data(self, market_name: str) -> pd.DataFrame:
        return self.market_data.get(market_name)

    def get_markets(self) -> list:
        return list(self.market_data.keys())

class TradeData:
    def __init__(self, trade_files: Dict[str, Dict[str, str]]):
        self.trade_data = {}
        self.minio = MinioClient()
        self.load_trades(trade_files)

    def load_trades(self, trade_files: Dict[str, Dict[str, str]]) -> None:
        for market_name, file_info in trade_files.items():
            data = self.minio.get_object(file_info["bucket"], file_info["file"])
            df = pd.read_parquet(io.BytesIO(data))
            df['entry_date'] = pd.to_datetime(df['entry_date'], unit='ms')
            df['exit_date'] = pd.to_datetime(df['exit_date'], unit='ms')
            self.trade_data[market_name] = df

    def get_trade_data(self, market_name: str) -> pd.DataFrame:
        return self.trade_data.get(market_name)

    def get_markets_with_trades(self) -> list:
        return list(self.trade_data.keys())