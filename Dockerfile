FROM ghcr.io/smart-social-contracts/icp-dev-env:latest@sha256:5445ccee3ce98b032a7bc0069081bd1e351c7576f3ccd4daaae0273e6fe29d60

WORKDIR /app

COPY requirements.txt ./requirements.txt
COPY requirements-dev.txt ./requirements-dev.txt
COPY package-lock.json ./package-lock.json
COPY package.json ./package.json
COPY tsconfig.json ./tsconfig.json
COPY scripts ./scripts
COPY src ./src
COPY tests ./tests
COPY dfx.json ./dfx.json
COPY canister_ids.json ./canister_ids.json

RUN ./scripts/setup_dev.sh
RUN ./scripts/download_wasms.sh