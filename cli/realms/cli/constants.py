"""Constants used throughout the CLI application."""

import os

MAX_BATCH_SIZE = 10

# Default realm folder
# Can be overridden with REALMS_FOLDER environment variable
DEFAULT_REALM_FOLDER = ".realms"
REALM_FOLDER = os.environ.get("REALMS_FOLDER", DEFAULT_REALM_FOLDER)
