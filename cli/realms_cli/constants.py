"""Constants used throughout the CLI application."""

import os

MAX_BATCH_SIZE = 100

# Docker image configuration
# Can be overridden with REALMS_DOCKER_IMAGE environment variable
DEFAULT_DOCKER_IMAGE = "ghcr.io/smart-social-contracts/realms:latest"  # TODO: this should be the image built in the latest release commit
DOCKER_IMAGE = os.environ.get("REALMS_DOCKER_IMAGE", DEFAULT_DOCKER_IMAGE)

# Default realm folder
# Can be overridden with REALMS_FOLDER environment variable
DEFAULT_REALM_FOLDER = ".realm"
REALM_FOLDER = os.environ.get("REALMS_FOLDER", DEFAULT_REALM_FOLDER)
