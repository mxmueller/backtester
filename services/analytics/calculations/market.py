import pandas as pd
from typing import List

def get_market_symbols(df: pd.DataFrame) -> List[str]:
    return df['symbol'].unique().tolist()