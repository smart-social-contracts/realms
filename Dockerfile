FROM ghcr.io/smart-social-contracts/icp-dev-env:latest

COPY src/local/requirements.txt /app/src/local/requirements.txt
COPY src/canister_main/requirements.txt /app/src/canister_main/requirements.txt

RUN pip install -r /app/src/local/requirements.txt
RUN pip install -r /app/src/canister_main/requirements.txt

RUN npm install