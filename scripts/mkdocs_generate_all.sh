#!/usr/bin/env bash

set -e
set -x

uv run python scripts/mkdocs_generate_reference.py
uv run python scripts/mkdocs_generate_release_notes.py
