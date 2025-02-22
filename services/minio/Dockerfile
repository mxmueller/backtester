FROM minio/minio:latest

RUN curl -O https://dl.min.io/client/mc/release/linux-amd64/mc && \
    chmod +x mc && \
    mv mc /usr/local/bin/

COPY setup.sh /setup.sh
RUN chmod +x /setup.sh

COPY ftse_daily.parquet /ftse_daily.parquet
COPY nasdaq_daily.parquet /nasdaq_daily.parquet
COPY ftse_trades2.parquet /ftse_trades2.parquet
COPY ftse_trades.parquet /ftse_trades.parquet

ENV MINIO_ROOT_USER=minioadmin
ENV MINIO_ROOT_PASSWORD=minioadmin

EXPOSE 9000 9001

ENTRYPOINT ["/setup.sh"]