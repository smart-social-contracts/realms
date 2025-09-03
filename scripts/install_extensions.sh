#!/bin/bash


set -e
set -x

echo "Installing extensions using realms CLI..."

realms extension install-from-source --source-dir extensions

echo "Extensions installed successfully"
