#!/usr/bin/env bash

set -e

command=( "$@" )
if [ "${#command[@]}" -eq 0 ]; then
  command=( "pytest" )
fi

chrome_cmd=("google-chrome")
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  chrome_cmd=("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
fi
chrome_cmd+=("--version")

chrome_version="${chrome_cmd[@]}"
echo "Chrome version: $chrome_version"

set -x
uv run "${command[@]}"
