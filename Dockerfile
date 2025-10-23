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

# Copy CLI directory before setup script runs (needed for pip install -e cli/)
COPY cli ./cli

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
COPY realm_config.json ./realm_config.json

# Source code
COPY scripts ./scripts
COPY src ./src
COPY tests ./tests
COPY extensions ./extensions

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
