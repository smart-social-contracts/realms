#!/bin/bash

pip install -r src/canister_main/requirements.txt
pip install -r src/local/requirements.txt
pip install -r requirements-dev.txt

python -m kybra install-dfx-extension

npm ci