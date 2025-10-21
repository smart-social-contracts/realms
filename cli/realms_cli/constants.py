"""Constants used throughout the CLI application."""

import os

MAX_BATCH_SIZE = 100

# Docker image configuration
# Can be overridden with REALMS_DOCKER_IMAGE environment variable
DEFAULT_DOCKER_IMAGE = "ghcr.io/smart-social-contracts/realms:3320d72c4e9a5ca2436b867c33a9337db74eaa37"
DOCKER_IMAGE = os.environ.get("REALMS_DOCKER_IMAGE", DEFAULT_DOCKER_IMAGE)
