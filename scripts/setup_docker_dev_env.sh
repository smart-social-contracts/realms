#!/bin/bash

set -e
set -x

pip install -r requirements.txt
pip install -r requirements-dev.txt

python -m kybra install-dfx-extension
