#!/bin/bash

set -e

PYTHON_VERSION="3.10"
NODE_VERSION="22"
ICP_CLI_VERSION="0.2"
BASILISK_VERSION="0.8.0"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
    exit 1
}

check_ubuntu() {
    if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
        error "This script is designed for Ubuntu systems only"
    fi
    log "Detected Ubuntu system"
}

install_system_dependencies() {
    log "Installing system dependencies..."
    
    sudo apt-get update
    sudo apt-get install -y curl ca-certificates libunwind8 build-essential git
    
    log "System dependencies installed successfully"
}

install_pyenv() {
    if command -v pyenv >/dev/null 2>&1; then
        log "pyenv already installed"
    else
        error "pyenv is required for this script. Please install pyenv first."
    fi
}

install_python() {
    # Use pyenv shell to activate Python 3.10
    log "Activating Python $PYTHON_VERSION with pyenv..."
    
    # Check if Python version is installed
    if ! pyenv versions --bare | grep -q "^$PYTHON_VERSION"; then
        log "Python $PYTHON_VERSION not found in pyenv, installing..."
        pyenv install -q "$PYTHON_VERSION"
    fi
    
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"

    # Activate Python 3.10
    pyenv shell "$PYTHON_VERSION"
    
    # Verify Python version
    python_version=$(python --version 2>&1 | cut -d' ' -f2)
    if [[ "$python_version" == "$PYTHON_VERSION"* ]]; then
        log "Python $python_version activated successfully"
    else
        error "Failed to activate Python $PYTHON_VERSION. Current version: $python_version"
    fi
}

install_node() {
    if command -v node >/dev/null 2>&1; then
        current_node_version=$(node --version | sed 's/v//')
        if [[ "$current_node_version" == "$NODE_VERSION"* ]]; then
            log "Node.js $NODE_VERSION already installed"
            return
        fi
    fi
    
    log "Installing Node.js $NODE_VERSION..."
    
    sudo apt-get install -y npm
    sudo npm install -g n
    sudo n "$NODE_VERSION"
    
    export PATH="/usr/local/bin:$PATH"
    
    node_version=$(node --version 2>/dev/null | sed 's/v//' || echo "")
    if [[ "$node_version" == "$NODE_VERSION"* ]]; then
        log "Node.js $NODE_VERSION installed successfully"
    else
        error "Failed to install Node.js $NODE_VERSION. Current version: $node_version"
    fi
}

install_icp_cli() {
    if command -v icp >/dev/null 2>&1; then
        log "icp CLI already installed"
        return
    fi
    
    log "Installing icp CLI..."
    
    npm install -g @icp-sdk/icp-cli
    
    export PATH="$HOME/.local/share/icp/bin:$PATH"
    echo 'export PATH="$HOME/.local/share/icp/bin:$PATH"' >> ~/.bashrc
    
    if command -v icp >/dev/null 2>&1; then
        log "icp CLI installed successfully: $(icp --version)"
    else
        error "Failed to install icp CLI"
    fi
}

install_basilisk() {
    # Ensure Python 3.10 is active
    pyenv shell "$PYTHON_VERSION"
    
    if python -c "import basilisk; print(basilisk.__version__)" 2>/dev/null | grep -q "$BASILISK_VERSION"; then
        log "Basilisk $BASILISK_VERSION already installed"
    else
        log "Installing Basilisk $BASILISK_VERSION..."
        pip install --no-cache-dir "ic-basilisk==$BASILISK_VERSION"
    fi
    
    log "Installing Basilisk extension..."
    python -m basilisk install-dfx-extension
    
    log "Basilisk installed successfully"
}

install_basilisk_prerequisites() {
    log "Installing Basilisk prerequisites by deploying test canister..."
    
    export PATH="$HOME/.local/share/icp/bin:$PATH"
    # Ensure Python 3.10 is active
    pyenv shell "$PYTHON_VERSION"
    
    temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    echo 'from basilisk import query, text

@query
def greet() -> text:
    return "Hello"' > main.py
    
    printf 'canisters:\n- name: test\n  build:\n    steps:\n    - type: script\n      commands:\n      - CANISTER_CANDID_PATH=.basilisk/test/test.did python -m basilisk test main.py\n      - cp .basilisk/test/test.wasm "$ICP_WASM_OUTPUT_PATH"\n' > icp.yaml
    
    icp network start -d
    icp deploy
    icp network stop
    
    cd "$PROJECT_ROOT"
    rm -rf "$temp_dir"
    
    log "Basilisk prerequisites installed successfully"
}

setup_project_dependencies() {
    log "Setting up project dependencies..."
    
    cd "$PROJECT_ROOT"
    
    # Ensure Python 3.10 is active
    pyenv shell "$PYTHON_VERSION"
    
    if [[ -f "requirements.txt" ]]; then
        log "Installing Python requirements..."
        pip install -r requirements.txt
    fi
    
    if [[ -f "requirements-dev.txt" ]]; then
        log "Installing Python development requirements..."
        pip install -r requirements-dev.txt
    fi
    
    python -m basilisk install-dfx-extension
    
    if [[ -f "package.json" ]]; then
        log "Installing Node.js dependencies..."
        npm install --legacy-peer-deps
    fi
    
    log "Installing Playwright..."
    npx playwright install
    
    log "Project dependencies installed successfully"
}

verify_installation() {
    log "Verifying installation..."
    
    export PATH="$HOME/.local/share/icp/bin:$PATH"
    # Ensure Python 3.10 is active
    pyenv shell "$PYTHON_VERSION"
    
    log "Python version: $(python --version)"
    log "Node version: $(node --version)"
    log "icp version: $(icp --version)"
    
    if python -c "import basilisk; print(f'Basilisk version: {basilisk.__version__}')" 2>/dev/null; then
        log "Basilisk installation verified"
    else
        error "Basilisk verification failed"
    fi
    
    log "All installations verified successfully!"
}

cleanup_on_error() {
    log "Cleaning up due to error..."
    icp network stop 2>/dev/null || true
}

main() {
    trap cleanup_on_error ERR
    
    log "Starting ICP development environment setup..."
    log "Target versions: Python $PYTHON_VERSION, Node $NODE_VERSION, icp CLI, Basilisk $BASILISK_VERSION"
    log "Note: This script installs core dependencies only. No canisters will be built or deployed."
    
    check_ubuntu
    install_system_dependencies
    install_pyenv
    install_python
    install_node
    install_icp_cli
    install_basilisk
    install_basilisk_prerequisites
    setup_project_dependencies
    verify_installation
    
    log "ICP development environment setup completed successfully!"
    log "Please restart your terminal or run 'source ~/.bashrc' to ensure all PATH changes take effect."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
