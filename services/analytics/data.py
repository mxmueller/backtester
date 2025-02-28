import pandas as pd
import pyarrow.parquet as pq
import io
import os
from minio import Minio
from typing import Dict, Any, List, Optional
from config import minio_config, markets, get_market_path, get_strategies_path


class MinioClient:
    def __init__(self):
        self.client = Minio(
            "minio:9000",
            access_key=minio_config["access_key"],
            secret_key=minio_config["secret_key"],
            secure=minio_config["secure"]
        )

    def get_object(self, path: str) -> bytes:
        bucket, *parts = path.split('/')
        object_path = '/'.join(parts)
        try:
            data = self.client.get_object(bucket, object_path)
            return data.read()
        except Exception as e:
            print(f"Error reading from MinIO: {e}")
            raise

    def get_object_tags(self, path: str) -> Dict[str, str]:
        bucket, *parts = path.split('/')
        object_path = '/'.join(parts)
        try:
            tags = self.client.get_object_tags(bucket, object_path)
            return tags
        except Exception as e:
            print(f"Error reading tags from MinIO: {e}")
            raise

    def list_objects(self, path: str) -> List[str]:
        bucket, *parts = path.split('/')
        prefix = '/'.join(parts) + '/' if parts else ''
        try:
            objects = self.client.list_objects(bucket, prefix=prefix)
            return [obj.object_name for obj in objects]
        except Exception as e:
            print(f"Error listing objects from MinIO: {e}")
            raise


class MarketData:
    def __init__(self):
        self.market_data = {}
        self.minio = MinioClient()
        self.load_markets()

    def load_markets(self) -> None:
        for market_name, market_info in markets.items():
            market_path = f"{get_market_path(market_name)}/{market_info['market_data']}"
            data = self.minio.get_object(market_path)
            df = pd.read_parquet(io.BytesIO(data))
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            self.market_data[market_name.upper()] = df

    def get_market_data(self, market_name: str) -> Optional[pd.DataFrame]:
        return self.market_data.get(market_name.upper())

    def get_markets(self) -> List[str]:
        return list(self.market_data.keys())


class TradeData:
    def __init__(self):
        self.minio = MinioClient()

    def load_strategy(self, market_name: str, strategy_version: str) -> pd.DataFrame:
        strategy_path = f"{get_strategies_path(market_name)}/{strategy_version}.parquet"
        data = self.minio.get_object(strategy_path)
        df = pd.read_parquet(io.BytesIO(data))
        df['entry_date'] = pd.to_datetime(df['entry_date'], unit='ms')
        df['exit_date'] = pd.to_datetime(df['exit_date'], unit='ms')
        return df

    def get_strategy_metadata(self, market_name: str, strategy_version: str) -> Dict[str, str]:
        strategy_path = f"{get_strategies_path(market_name)}/{strategy_version}.parquet"
        return self.minio.get_object_tags(strategy_path)

    def list_strategies(self, market_name: str) -> List[Dict[str, Any]]:
        strategies_path = get_strategies_path(market_name)
        strategy_files = self.minio.list_objects(strategies_path)

        strategies = []
        for file in strategy_files:
            if not file.endswith('.parquet'):
                continue
            version = file.split('/')[-1].replace('.parquet', '')
            metadata = self.get_strategy_metadata(market_name, version)
            strategies.append({
                'version': version,
                'metadata': metadata
            })
        return strategies