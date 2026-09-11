#!/usr/bin/env bash
# USB volume names. ISO9660 (live OS) + exFAT (data). Spaces are intentional.
# shellcheck disable=SC2034

CEREMONY_OS_LABEL="${CEREMONY_OS_LABEL:-CEREMONY OS}"
CEREMONY_DATA_LABEL="${CEREMONY_DATA_LABEL:-CEREMONY DATA}"
# Older sticks used these; keep them as lookup aliases until relabeled.
CEREMONY_DATA_LABEL_ALIASES="${CEREMONY_DATA_LABEL_ALIASES:-REALMS_DATA}"
