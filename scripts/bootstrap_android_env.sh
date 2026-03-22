#!/usr/bin/env bash
set -euo pipefail

echo "Check Java:"
command -v java || true
echo "Check ADB:"
command -v adb || true
echo "Check Maestro:"
command -v maestro || true
echo "ANDROID_SDK_ROOT=${ANDROID_SDK_ROOT:-}"
