FROM ghcr.io/smart-social-contracts/icp-dev-env:latest

RUN pip install kybra_simple_db

# TODO: copy the contents of the library directly yo the src folder


RUN pip install -r src/local/requirements.txt
RUN pip install -r src/canister_main/requirements.txt
RUN pip install -r tests/requirements-test.txt

