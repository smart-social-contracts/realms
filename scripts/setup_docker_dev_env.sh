#!/bin/bash

set -e
set -x

python -m venv venv
source /venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

python -m kybra install-dfx-extension
