FROM ghcr.io/smart-social-contracts/icp-dev-env:db60540

WORKDIR /app

COPY scripts/download_wasms.sh ./scripts/download_wasms.sh
RUN ./scripts/download_wasms.sh

# Dependencies
COPY requirements.txt ./requirements.txt
COPY requirements-dev.txt ./requirements-dev.txt
COPY package-lock.json ./package-lock.json
COPY package.json ./package.json
COPY ./scripts/setup_docker_dev_env.sh ./scripts/setup_docker_dev_env.sh
RUN ./scripts/setup_docker_dev_env.sh

# Install playwright UI testing framework and dependencies
COPY ./src/realm_frontend/package.json ./src/realm_frontend/package.json
RUN cd src/realm_frontend && npm install --legacy-peer-deps && npx --no -- playwright install --with-deps

# Configuration files
COPY .flake8 ./.flake8
COPY mypy.ini ./mypy.ini
COPY tsconfig.json ./tsconfig.json
COPY dfx.json ./dfx.json
COPY canister_ids.json ./canister_ids.json
COPY pyproject.toml ./pyproject.toml

# Source code
COPY scripts ./scripts
COPY src ./src
COPY tests ./tests
COPY extensions ./extensions

# Install extensions
RUN scripts/install_extensions.sh

# Build canisters
RUN scripts/build_canisters.sh