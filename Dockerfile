FROM ghcr.io/smart-social-contracts/icp-dev-env:db60540 AS base

RUN apt-get update && apt-get install -y --no-install-recommends procps nano && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies
COPY requirements.txt ./requirements.txt
COPY requirements-dev.txt ./requirements-dev.txt
COPY package-lock.json ./package-lock.json
COPY package.json ./package.json
COPY ./scripts/setup_docker_dev_env.sh ./scripts/setup_docker_dev_env.sh

# Copy CLI directory before setup script runs (needed for pip install -e cli/)
COPY cli ./cli

RUN ./scripts/setup_docker_dev_env.sh


# Configuration files
COPY .flake8 ./.flake8
COPY mypy.ini ./mypy.ini
COPY tsconfig.json ./tsconfig.json
COPY dfx.json ./dfx.json
COPY pyproject.toml ./pyproject.toml
COPY realm_config.json ./realm_config.json

# Source code
COPY scripts ./scripts
COPY src ./src
COPY tests ./tests
COPY examples ./examples

RUN touch src/realm_backend/extension_packages/extension_imports.py

# Generate extension manifests (create empty file with proper structure for Docker build)
RUN echo '"""' > src/realm_backend/extension_packages/extension_manifests.py && \
    echo 'Static extension manifest registry for Kybra canister environment.' >> src/realm_backend/extension_packages/extension_manifests.py && \
    echo 'This file will be regenerated during deployment.' >> src/realm_backend/extension_packages/extension_manifests.py && \
    echo '"""' >> src/realm_backend/extension_packages/extension_manifests.py && \
    echo '' >> src/realm_backend/extension_packages/extension_manifests.py && \
    echo 'EXTENSION_MANIFESTS = {}' >> src/realm_backend/extension_packages/extension_manifests.py && \
    echo '' >> src/realm_backend/extension_packages/extension_manifests.py && \
    echo 'def get_all_extension_manifests() -> dict:' >> src/realm_backend/extension_packages/extension_manifests.py && \
    echo '    """Get all extension manifests"""' >> src/realm_backend/extension_packages/extension_manifests.py && \
    echo '    return EXTENSION_MANIFESTS' >> src/realm_backend/extension_packages/extension_manifests.py

# Demo stage: extends base and adds extensions folder for testing/demos
FROM base AS demo
COPY extensions ./extensions

FROM demo AS test

FROM test AS ui-test
# Install playwright UI testing framework and dependencies
COPY ./src/realm_frontend/package.json ./src/realm_frontend/package.json
RUN cd src/realm_frontend && npm install --legacy-peer-deps && npx --no -- playwright install --with-deps
