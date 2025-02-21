#!/bin/bash

BUCKET1="market-data"
BUCKET2="trading-data"

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

mc mb myminio/$BUCKET1
mc mb myminio/$BUCKET2

FILE1="ftse_daily.parquet"
FILE2="ftse_trades.parquet"

mc cp /"$FILE1" myminio/"$BUCKET1"/
mc tag set myminio/"$BUCKET1"/"$FILE1" "project=Test&version=1.0"

mc cp /"$FILE2" myminio/"$BUCKET2"/
mc tag set myminio/"$BUCKET2"/"$FILE2" "project=Test&version=1.0"

wait