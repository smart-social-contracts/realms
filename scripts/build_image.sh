#!/bin/bash

./scripts/cleanup.sh

# First, build the image
docker build -t smart-social-contracts/realms:latest .

