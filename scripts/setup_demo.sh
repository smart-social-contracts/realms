#!/bin/bash

set -e
set -x

realms create --random
realms deploy --file .realm/realm_config.json
