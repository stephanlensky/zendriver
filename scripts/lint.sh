#!/usr/bin/env bash

set -e
set -x

python_files=(zendriver scripts examples tests)

echo "Running ruff check..."
uv run ruff check "${python_files[@]}"
echo "Running ruff format check..."
uv run ruff format "${python_files[@]}" --check
echo "Running mypy..."
uv run mypy "${python_files[@]}"
