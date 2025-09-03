#!/bin/bash

set -e
set -x

realms create --random
realms deploy --file generated_realm/realm_config.json
