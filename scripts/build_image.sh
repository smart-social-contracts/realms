#!/bin/bash

./scripts/cleanup.sh

# First, build the image
docker build --no-cache -t smart-social-contracts/realms:latest .

