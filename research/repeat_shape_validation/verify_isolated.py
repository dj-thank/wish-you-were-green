#!/usr/bin/env python3
"""Replay in a temporary minimal tree while denying Python socket connections."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    previous = json.loads((HERE / 'verification.json').read_text())
    assert previous['status'] == 'PASS'
    source_hashes = dict(previous['verified_file_sha256'])
    # This harness may be created after the first full verification.
    source_hashes[str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__))
    source_hashes.pop('research/repeat_shape_validation/isolated_replay.json', None)
    for name, expected in source_hashes.items():
        assert sha(ROOT / name) == expected, name
    with tempfile.TemporaryDirectory(prefix='wish-green-repeat-isolated-') as temporary:
        isolated = Path(temporary) / 'repo'
        for name in source_hashes:
            destination = isolated / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        assert not (isolated / 'sdss/raw').exists()
        assert not (isolated / 'mwdd/spectra').exists()
        child = '''
import importlib.util, json, socket, sys
from pathlib import Path
sys.dont_write_bytecode = True
def blocked(*args, **kwargs):
    raise RuntimeError("Network connection forbidden during isolated replay")
socket.socket.connect = blocked
socket.socket.connect_ex = blocked
socket.create_connection = blocked
root = Path.cwd()
path = root / "research/repeat_shape_validation/verify_outputs.py"
spec = importlib.util.spec_from_file_location("repeat_shape_isolated_verifier", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(json.dumps(module.verify(root)))
'''
        run = subprocess.run([sys.executable, '-c', child], cwd=isolated,
                             check=True, text=True, capture_output=True)
        verified = json.loads(run.stdout)
        assert verified['verified_file_sha256'] == source_hashes
        result = dict(status='PASS', completed_utc=datetime.now(timezone.utc).isoformat(),
                      protocol='A fresh temporary tree contains only the individually hashed replay inputs and source/artifact files; sdss/raw and mwdd/spectra are absent. Python socket connect/connect_ex/create_connection raise errors. verify(root) is imported in a new interpreter with the temporary tree as cwd.',
                      network_connections_denied=True, large_survey_cache_present=False,
                      copied_files=len(source_hashes),
                      copied_bytes=sum((ROOT / name).stat().st_size for name in source_hashes),
                      summary=verified['summary'], tested_file_sha256=source_hashes,
                      stderr=run.stderr,
                      limits='A numerical/evidence replay, not a second visual inspection or an independently implemented physical calibration model.')
    (HERE / 'isolated_replay.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'copied_files', 'copied_bytes',
                     'network_connections_denied', 'large_survey_cache_present']}, indent=2))


if __name__ == '__main__':
    main()
