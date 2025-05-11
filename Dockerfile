FROM ghcr.io/smart-social-contracts/icp-dev-env:latest

COPY src/local/requirements.txt /app/src/local/requirements.txt
COPY src/realm_backend/requirements.txt /app/src/realm_backend/requirements.txt

RUN pip install -r /app/src/local/requirements.txt
RUN pip install -r /app/src/realm_backend/requirements.txt

RUN npm install