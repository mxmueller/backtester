FROM minio/minio:latest

RUN curl -O https://dl.min.io/client/mc/release/linux-amd64/mc && \
    chmod +x mc && \
    mv mc /usr/local/bin/

RUN curl -L https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -o /usr/bin/yq && \
    chmod +x /usr/bin/yq

COPY setup.sh /setup.sh
RUN chmod +x /setup.sh

EXPOSE 9000 9001

ENTRYPOINT ["/setup.sh"]