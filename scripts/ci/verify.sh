#!/usr/bin/env bash
set -euo pipefail

python -m pip install --disable-pip-version-check --quiet 'pytest==9.1.1'
python -m compileall -q src tests scripts mastermind_sidecar.py
python -m pytest -q tests
python scripts/operate.py

gofmt -w src/countdown_timer.go src/countdown_timer_test.go
git diff --exit-code -- src/countdown_timer.go src/countdown_timer_test.go
go vet ./...
go test ./...

python scripts/verify_public_surface.py
