#!/usr/bin/env bash
exec bash "$(dirname -- "${BASH_SOURCE[0]}")/bsv.sh" stop "$@"
