"""Constants used throughout the CLI application."""

import os

MAX_BATCH_SIZE = 10  # Reduced from 25 to handle complex records with relationships (Zone+Land)

# Docker image configuration
# Updated automatically during release to match the current version
# Can be overridden with REALMS_DOCKER_IMAGE environment variable
DEFAULT_DOCKER_IMAGE = "ghcr.io/smart-social-contracts/realms:v0.2.8"
DOCKER_IMAGE = os.environ.get("REALMS_DOCKER_IMAGE", DEFAULT_DOCKER_IMAGE)

# Default realm folder
# Can be overridden with REALMS_FOLDER environment variable
DEFAULT_REALM_FOLDER = ".realms"
REALM_FOLDER = os.environ.get("REALMS_FOLDER", DEFAULT_REALM_FOLDER)
