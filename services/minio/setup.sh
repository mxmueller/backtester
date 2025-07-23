#!/bin/bash

CONFIG_FILE=${CONFIG_FILE:-/config/config.yaml}

MINIO_ROOT_USER=$(yq '.minio.user' $CONFIG_FILE)
MINIO_ROOT_PASSWORD=$(yq '.minio.password' $CONFIG_FILE)

BASE_BUCKET=$(yq '.storage.base_bucket' $CONFIG_FILE)
MARKETS=$(yq '.storage.markets[].name' $CONFIG_FILE)

# MinIO im Hintergrund starten
minio server /data --console-address ":9001" &

# Richtige Warteschleife - warte bis MinIO bereit ist
echo "Warte auf MinIO Server..."
READY_CHECK_LOOP=0
MAX_READY_CHECK_LOOPS=30
while true; do
  if mc alias set myminio http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" 2>/dev/null; then
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

# Jetzt erstelle die Buckets (MinIO ist bereit)
mc mb myminio/$BASE_BUCKET

for MARKET in $MARKETS; do
    mc mb myminio/$BASE_BUCKET/$MARKET
    mc mb myminio/$BASE_BUCKET/$MARKET/strategies

    DATA_PATH=$(yq ".storage.markets[] | select(.name == \"$MARKET\") | .data_path" $CONFIG_FILE)
    DATA_FILE=$(yq ".storage.markets[] | select(.name == \"$MARKET\") | .data_file" $CONFIG_FILE)
    mc cp $DATA_PATH myminio/$BASE_BUCKET/$MARKET/$DATA_FILE
    mc tag set myminio/$BASE_BUCKET/$MARKET/$DATA_FILE "project=Test&version=1.0" 2>/dev/null || true

    STRATEGIES_COUNT=$(yq ".storage.markets[] | select(.name == \"$MARKET\") | .strategies | length" $CONFIG_FILE)

    for ((i=0; i<$STRATEGIES_COUNT; i++)); do
        SOURCE_PATH=$(yq ".storage.markets[] | select(.name == \"$MARKET\") | .strategies[$i].source_path" $CONFIG_FILE)
        DEST_FILE=$(yq ".storage.markets[] | select(.name == \"$MARKET\") | .strategies[$i].file" $CONFIG_FILE)
        STRAT_TYPE=$(yq ".storage.markets[] | select(.name == \"$MARKET\") | .strategies[$i].type" $CONFIG_FILE)
        VERSION_DESC=$(yq ".storage.markets[] | select(.name == \"$MARKET\") | .strategies[$i].description" $CONFIG_FILE)
        PAIR_FINDING=$(yq ".storage.markets[] | select(.name == \"$MARKET\") | .strategies[$i].pair_finding" $CONFIG_FILE)

        mc cp $SOURCE_PATH myminio/$BASE_BUCKET/$MARKET/strategies/$DEST_FILE
        mc tag set myminio/$BASE_BUCKET/$MARKET/strategies/$DEST_FILE "strategy_type=$STRAT_TYPE&version_description=$VERSION_DESC&pair_finding=$PAIR_FINDING" 2>/dev/null || true
    done
done

echo "Setup complete - buckets and files ready!"
wait