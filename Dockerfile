FROM ghcr.io/smart-social-contracts/icp-dev-env:latest

RUN pip install kybra_simple_db

# TODO: copy the contents of the library directly yo the src folder
COPY src/local/requirements.txt /app/src/local/requirements.txt
COPY src/canister_main/requirements.txt /app/src/canister_main/requirements.txt

RUN pip install -r /app/src/local/requirements.txt
RUN pip install -r /app/src/canister_main/requirements.txt

