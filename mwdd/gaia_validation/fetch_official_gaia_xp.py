"""Fetch public Gaia XP coefficient data through documented ESA DataLink.

Usage: python fetch_official_gaia_xp.py SOURCE_ID PREFIX
Only the supplied public Gaia source ID is queried. Access URLs are obtained
from the DataLink result; no catalogue scans or guessed data paths are used.
"""
from pathlib import Path
import sys
import re
import json
import hashlib
from datetime import datetime, timezone
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
source_id, prefix = sys.argv[1:]
if not source_id.isdigit() or re.fullmatch(r'j[0-9]+', prefix) is None:
    raise ValueError('Numeric source ID and a j+digits prefix required')

def fetch(url, path):
    sidecar = path.with_suffix(path.suffix + '.source.json')
    if path.exists() and sidecar.exists():
        data = path.read_bytes()
        old = json.loads(sidecar.read_text())
        if hashlib.sha256(data).hexdigest() != old['sha256']:
            raise ValueError(f'Cached download checksum mismatch: {path.name}')
        return data
    req = urllib.request.Request(url, headers={'User-Agent': 'Public-spectrum-validation/1.0'})
    with urllib.request.urlopen(req, timeout=90) as response:
        data = response.read()
        record = {'url': url, 'final_url': response.url, 'status': response.status,
                  'content_type': response.headers.get('Content-Type'),
                  'retrieved_utc': datetime.now(timezone.utc).isoformat(),
                  'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                  'path': path.name}
    path.write_bytes(data)
    sidecar.write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)
    return data

url = 'https://gea.esac.esa.int/data-server/datalink/links?' + urllib.parse.urlencode({'ID': f'Gaia DR3 {source_id}'})
xml = fetch(url, ROOT / f'{prefix}_datalink.xml')
table = ET.fromstring(xml).find('.//{*}TABLE')
fields = [e.attrib['name'] for e in table.findall('{*}FIELD')]
rows = [dict(zip(fields, [(cell.text or '') for cell in row.findall('{*}TD')]))
        for row in table.findall('.//{*}TABLEDATA/{*}TR')]
links = [r['access_url'] for r in rows if 'RETRIEVAL_TYPE=XP_CONTINUOUS' in r.get('access_url', '')]
if len(links) != 1:
    raise RuntimeError(f'Expected one XP_CONTINUOUS access URL; DataLink rows: {rows}')
data_url = links[0] + '&FORMAT=CSV'
if urllib.parse.urlsplit(data_url).hostname != 'gea.esac.esa.int':
    raise RuntimeError('Unexpected DataLink host; review manually')
fetch(data_url, ROOT / f'{prefix}_xp_continuous.csv')
