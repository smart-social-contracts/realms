#!/bin/bash

set -e
set -x

realms realm create --random
realms realm deploy
