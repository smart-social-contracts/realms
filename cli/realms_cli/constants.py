"""Constants used throughout the CLI application."""

import os

MAX_BATCH_SIZE = 25  # Reduced from 100 to avoid ICP instruction limit (40B) on large records

# Docker image configuration
# Updated automatically during release to match the current version
# Can be overridden with REALMS_DOCKER_IMAGE environment variable
DEFAULT_DOCKER_IMAGE = "ghcr.io/smart-social-contracts/realms:v0.1.5"
DOCKER_IMAGE = os.environ.get("REALMS_DOCKER_IMAGE", DEFAULT_DOCKER_IMAGE)

# Default realm folder
# Can be overridden with REALMS_FOLDER environment variable
DEFAULT_REALM_FOLDER = ".realms"
REALM_FOLDER = os.environ.get("REALMS_FOLDER", DEFAULT_REALM_FOLDER)
