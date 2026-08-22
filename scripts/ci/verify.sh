#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR=".verification-artifacts"
MISSION_SCENARIO="${ARTIFACT_DIR}/mission-sequence.json"
MISSION_RECEIPT="${ARTIFACT_DIR}/mission-sequence.receipt.json"
mkdir -p "${ARTIFACT_DIR}"

python -m pip install --disable-pip-version-check --quiet 'pytest==9.1.1'
python -m compileall -q src tests scripts mastermind_sidecar.py
python -m pytest -q tests | tee "${ARTIFACT_DIR}/pytest.txt"
python scripts/operate.py | tee "${ARTIFACT_DIR}/operate.txt"
python scripts/mission_sequence_probe.py \
  --output "${MISSION_SCENARIO}" \
  --receipt "${MISSION_RECEIPT}" \
  | tee "${ARTIFACT_DIR}/mission-sequence-probe.txt"

python - <<'PY'
import hashlib
import json
from pathlib import Path

scenario_path = Path('.verification-artifacts/mission-sequence.json')
receipt_path = Path('.verification-artifacts/mission-sequence.receipt.json')
scenario = json.loads(scenario_path.read_text(encoding='utf-8'))
receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
assert scenario['evidence_state'] == 'DETERMINISTIC_PORTFOLIO_MISSION_SEQUENCE_MODEL'
assert [row['action'] for row in scenario['timeline']] == scenario['expected_actions']
assert any(row['missing_gates'] for row in scenario['timeline'])
assert any('range:DISAGREEMENT' in row['active_holds'] for row in scenario['timeline'])
assert scenario['timeline'][-1]['stage_after'] == 'COMPLETE'
actual = hashlib.sha256(scenario_path.read_bytes()).hexdigest()
assert receipt['artifact_sha256'] == actual
assert receipt['verified_state'] == 'MISSION_SEQUENCE_SCENARIO_EXECUTED'
assert receipt['terminal_stage'] == 'COMPLETE'
print(json.dumps({
    'mission_sequence': 'PASS',
    'actions': scenario['expected_actions'],
    'artifact_sha256': actual,
}, indent=2))
PY

gofmt -w src/countdown_timer.go src/countdown_timer_test.go
git diff --exit-code -- src/countdown_timer.go src/countdown_timer_test.go
go vet ./...
go test ./...

python scripts/verify_public_surface.py
