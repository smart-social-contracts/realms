#!/bin/bash

set -e
set -x

# Get current branch name (fallback to default if git is not available)
if whereis git | grep -q "/"; then
    BRANCH_NAME=$(git branch --show-current 2>/dev/null || echo "main")

    # Set port based on branch (main uses default 8000, others get unique ports)
    if [ "$BRANCH_NAME" = "main" ]; then
        PORT=8000
    else
        # Generate unique port based on branch name hash
        PORT=$((8001 + $(echo $BRANCH_NAME | cksum | cut -d' ' -f1) % 99))
    fi

    echo "Deploying branch '$BRANCH_NAME' on port $PORT"

else
    PORT=8000
    echo "Git not available, using default port $PORT"
fi


# Check if virtual environment is activated, if not activate it
if [[ "$VIRTUAL_ENV" == "" ]]; then
    
    # Check if venv folder exists and activate it
    if [ -d "venv" ]; then
        echo "Virtual environment found, activating..."
        source venv/bin/activate
        echo "Virtual environment activated: $VIRTUAL_ENV"
    else
        echo "Virtual environment not detected, please create it"
        exit 1
    fi
else
    echo "Virtual environment already active: $VIRTUAL_ENV"
fi

# Only stop dfx processes using our specific port
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
dfx stop 2>/dev/null || true
dfx start --clean --background --host 127.0.0.1:$PORT --logfile dfx.log
dfx deploy internet_identity
scripts/install_extensions.sh
dfx deploy realm_backend --yes
dfx generate realm_backend
npm install --legacy-peer-deps
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend
sh scripts/update_config.sh
dfx deploy realm_frontend
scripts/setup_demo.sh