FROM minio/minio:latest

RUN curl -O https://dl.min.io/client/mc/release/linux-amd64/mc && \
    chmod +x mc && \
    mv mc /usr/local/bin/

COPY setup.sh /setup.sh
RUN chmod +x /setup.sh

# Kopiere deine Parquet-Dateien ins Image (z.B. ins Root-Verzeichnis)
COPY ftse_daily.parquet /ftse_daily.parquet
COPY ftse_trades.parquet /ftse_trades.parquet

ENV MINIO_ROOT_USER=minioadmin
ENV MINIO_ROOT_PASSWORD=minioadmin

EXPOSE 9000 9001

ENTRYPOINT ["/setup.sh"]