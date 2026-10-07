#!/usr/bin/env bash
# Alias — prefer run_bakeoff.sh for the same-dataset comparison story
exec "$(dirname "$0")/run_bakeoff.sh" "$@"
