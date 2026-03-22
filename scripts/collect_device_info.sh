#!/usr/bin/env bash
set -euo pipefail

ADB_BIN="${ADB_BIN:-adb}"
SERIAL="${1:-}"

if [[ -n "$SERIAL" ]]; then
  prefix=("$ADB_BIN" -s "$SERIAL")
else
  prefix=("$ADB_BIN")
fi

"${prefix[@]}" shell getprop ro.product.model
"${prefix[@]}" shell getprop ro.build.version.release
"${prefix[@]}" shell wm size
