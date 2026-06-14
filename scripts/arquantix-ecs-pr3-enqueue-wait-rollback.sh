#!/usr/bin/env bash
# PR3 — Rollback enqueue-and-wait : LIFI_ENQUEUE_AND_WAIT_ENABLED=false.
# Retour à la doctrine PR2 (409 fail-fast au confirm pour 2 swaps concurrents).
set -euo pipefail
export FLAG_VALUE=false
exec "$(dirname "$0")/arquantix-ecs-pr3-enqueue-wait-activate.sh"
