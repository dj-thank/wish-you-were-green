#!/usr/bin/env python3
"""Fetch the public Kepler et al. 2019 SDSS DR14 classification catalogue."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
import gzip
from pathlib import Path
import urllib.request
import urllib.parse

BASE = Path(__file__).resolve().parent
URL_BASE = 'https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/486/2169/'

def fetch(name):
    destination = BASE / 'catalogues' / name
    url = URL_BASE + name
    if name == 'table2.tsv':
        url = 'https://vizier.cds.unistra.fr/viz-bin/asu-tsv?' + urllib.parse.urlencode({
            '-source': 'J/MNRAS/486/2169/table2', '-out.all': '', '-out.max': '100000'
        })
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        data = destination.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=45) as response:
            data = response.read(15_000_001)
        if len(data) > 15_000_000:
            raise RuntimeError('Catalogue exceeded 15 MB size limit')
        destination.write_bytes(data)
    return dict(url=url, path=str(destination), bytes=len(data),
                sha256=sha256(data).hexdigest(),
                retrieved_utc=datetime.fromtimestamp(destination.stat().st_mtime,timezone.utc).isoformat())

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=2) as executor:
        records = list(executor.map(fetch, ['ReadMe', 'table2.dat.gz']))
    packed = BASE / 'catalogues' / 'table2.dat.gz'
    unpacked = BASE / 'catalogues' / 'table2.dat'
    unpacked.write_bytes(gzip.decompress(packed.read_bytes()))
    (BASE / 'catalogue_manifest.json').write_text(json.dumps(records, indent=2))
    print(json.dumps(records, indent=2))
