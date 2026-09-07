# Ubuntu 22.04 image for ceremony script tests (simulate mode — no YubiKey).
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DO_NOT_TRACK=1

RUN apt-get update -qq \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    jq \
    openssl \
    coreutils \
    util-linux \
    libdbus-1-3 \
    nodejs \
    npm \
  && npm install -g @icp-sdk/icp-cli@1.3.0 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /ceremony
COPY . /ceremony/

RUN chmod +x /ceremony/realms-key-ceremony.sh /ceremony/docker/test-ceremony.sh

CMD ["/ceremony/docker/test-ceremony.sh"]
