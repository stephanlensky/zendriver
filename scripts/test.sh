#!/usr/bin/env bash

set -e

command=( "$@" )
if [ "${#command[@]}" -eq 0 ]; then
  command=( "pytest" )
fi

chrome_executable=$(uv run python -c "from zendriver.core.config import find_chrome_executable;print(find_chrome_executable())")
echo "Chrome executable: $chrome_executable"

chrome_cmd=( "$chrome_executable" )
chrome_cmd+=("--version")
chrome_version=$("${chrome_cmd[@]}")
echo "Chrome version: $chrome_version"

set -x
uv run "${command[@]}"
