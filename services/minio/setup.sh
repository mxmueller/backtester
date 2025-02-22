#!/bin/bash

BASE_BUCKET="markets"
MARKET1="FTSE100"
MARKET2="NASDAQ100"

# Trading Strategie Files
TRADING1="ftse_trades.parquet"
TRADING2="ftse_trades2.parquet"

# Metadata Tags für Trading1
STRAT_TYPE1="Z-Score"
VERSION_DESC1="Initial Setup Version"
PAIR_FINDING1="Clustering"

# Metadata Tags für Trading2
STRAT_TYPE2="Z-Score"
VERSION_DESC2="Initial Setup Version Test"
PAIR_FINDING2="Clustering"

# Version IDs automatisch generieren (6-stelliger Hash)
VERSION1=$(head /dev/urandom | tr -dc a-f0-9 | head -c 6)
VERSION2=$(head /dev/urandom | tr -dc a-f0-9 | head -c 6)

minio server /data --console-address ":9001" &

READY_CHECK_LOOP=0
MAX_READY_CHECK_LOOPS=30
while true; do
  if mc config host list myminio 2>&1 | while read -r line; do [[ "$line" == *"myminio"* ]] && echo "ready" && break; done; then
    echo "MinIO-Server ist bereit."
    break
  fi
  if [ "$READY_CHECK_LOOP" -ge "$MAX_READY_CHECK_LOOPS" ]; then
    echo "Timeout beim Warten auf MinIO-Server."
    exit 1
  fi
  READY_CHECK_LOOP=$((READY_CHECK_LOOP + 1))
  echo "Warte auf den Start des MinIO-Servers... (Versuch $READY_CHECK_LOOP/$MAX_READY_CHECK_LOOPS)"
  sleep 2
done

mc alias set myminio http://localhost:9000 minioadmin minioadmin

# Erstelle Basis-Bucket und Strukturen
mc mb myminio/$BASE_BUCKET
mc mb myminio/$BASE_BUCKET/$MARKET1
mc mb myminio/$BASE_BUCKET/$MARKET1/strategies
mc mb myminio/$BASE_BUCKET/$MARKET2
mc mb myminio/$BASE_BUCKET/$MARKET2/strategies

# Kopiere Market Data
mc cp /ftse_daily.parquet myminio/$BASE_BUCKET/$MARKET1/market_data.parquet
mc tag set myminio/$BASE_BUCKET/$MARKET1/market_data.parquet "project=Test&version=1.0"

mc cp /nasdaq_daily.parquet myminio/$BASE_BUCKET/$MARKET2/market_data.parquet
mc tag set myminio/$BASE_BUCKET/$MARKET2/market_data.parquet "project=Test&version=1.0"

# Kopiere Trading Strategien
mc cp /"$TRADING1" myminio/$BASE_BUCKET/$MARKET1/strategies/version_${VERSION1}.parquet
mc tag set myminio/$BASE_BUCKET/$MARKET1/strategies/version_${VERSION1}.parquet "strategy_type=$STRAT_TYPE1&version_description=$VERSION_DESC1&pair_finding=$PAIR_FINDING1"

mc cp /"$TRADING2" myminio/$BASE_BUCKET/$MARKET1/strategies/version_${VERSION2}.parquet
mc tag set myminio/$BASE_BUCKET/$MARKET1/strategies/version_${VERSION2}.parquet "strategy_type=$STRAT_TYPE2&version_description=$VERSION_DESC2&pair_finding=$PAIR_FINDING2"

wait