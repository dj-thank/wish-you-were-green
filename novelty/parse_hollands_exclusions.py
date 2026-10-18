"""Extract all named stars in Hollands et al. 2026 Tables 3--6.

Offline input is an unmodified arXiv HTML download. Coordinates are decoded
from names, not newly measured astrometry. No epoch is inferred from a name.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

BASE = Path(__file__).resolve().parent
URL = 'https://arxiv.org/html/2610.18966v1'


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.selected = None
        self.rows = {}
        self.row = None
        self.cell = None
        self.skip_annotation = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table' and re.fullmatch(r'A3\.T[3-6]\.2', attrs.get('id', '')):
            self.selected = int(attrs['id'].split('.')[1][1:])
            self.rows[self.selected] = []
        if self.selected is None:
            return
        if tag == 'tr':
            self.row = []
        if tag in ('th', 'td'):
            self.cell = ''
        if tag == 'annotation':
            self.skip_annotation = True

    def handle_endtag(self, tag):
        if self.selected is None:
            return
        if tag == 'annotation':
            self.skip_annotation = False
        if tag in ('th', 'td') and self.cell is not None:
            self.row.append(re.sub(r'\s+', ' ', self.cell).strip().replace('−', '-'))
            self.cell = None
        if tag == 'tr' and self.row is not None:
            self.rows[self.selected].append(self.row)
            self.row = None
        if tag == 'table':
            self.selected = None

    def handle_data(self, data):
        if self.selected is not None and self.cell is not None and not self.skip_annotation:
            self.cell += data


def parse_pos(name):
    m = re.match(r'^(\d{2})(\d{2})(\d{2}\.\d+)([+-])(\d{2})(\d{2})(\d{2}\.\d+)(.*)$', name)
    if not m:
        raise ValueError(f'Unparsed WD position: {name!r}')
    hh, mm, ss, sign, dd, dm, ds, suffix = m.groups()
    ra = 15 * (int(hh) + int(mm) / 60 + float(ss) / 3600)
    dec = (int(dd) + int(dm) / 60 + float(ds) / 3600) * (1 if sign == '+' else -1)
    assert 0 <= ra < 360 and -90 <= dec <= 90
    short = f'WD J{hh}{mm}{sign}{dd}{dm}'
    return ra, dec, suffix.strip(), short


def main():
    raw = (BASE / 'hollands2026.html').read_bytes()
    parser = Tables()
    parser.feed(raw.decode('utf-8'))
    (BASE / 'hollands2026_tables_raw.json').write_text(json.dumps(parser.rows, ensure_ascii=False, indent=2))
    out = []
    table_kind = {3: 'IR-faint observed spectrum', 4: 'DQ observed spectrum',
                  5: 'DZ model fitted to a named object', 6: '20pc named object'}
    for n, rows in sorted(parser.rows.items()):
        for row in rows[1:]:
            if n in (3, 4, 5):
                if len(row) != 9:
                    raise ValueError(f'Table {n}: expected 9 cells, got {len(row)}')
                parts = [row[:4], row[5:9]]
            else:
                if len(row) != 10:
                    raise ValueError(f'Table 6: expected 10 cells, got {len(row)}')
                parts = [row]
            for p in parts:
                if not p[0]:
                    continue
                name = re.sub(r'\s+', '', p[0])
                ra, dec, component, short = parse_pos(name)
                if n < 6:
                    xy, cct, hexc = p[1:4]
                    alt = spt = teff = logg = ref = note = ''
                else:
                    alt, spt, teff, logg, xy, cct, hexc, ref, note = p[1:]
                xy = [float(x.strip()) for x in xy.strip('()').split(',')]
                out.append(dict(
                    name='WD J' + name, short_name=short, component=component,
                    alt_name=alt, ra_deg=round(ra, 10), dec_deg=round(dec, 10),
                    position_origin='encoded WD J designation',
                    coordinate_epoch='unknown; not inferred from designation',
                    coordinate_frame='not independently resolved',
                    table=n, source_category=table_kind[n], spectral_type=spt,
                    teff_k=teff.replace(' ', ''), logg=logg,
                    cie_x=xy[0], cie_y=xy[1],
                    cct_k=cct.replace(' ', '') if cct != '-' else '',
                    srgb_hex=hexc, original_ref=ref, original_note=note,
                    source_url=URL + '#A3.T' + str(n),
                    exclusion_reason='Perceived chromaticity already tabulated by Hollands et al. 2026',
                ))
    fieldnames = list(out[0])
    with (BASE / 'hollands2026_exclusions.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out)
    counts = dict(Counter(x['table'] for x in out))
    assert counts == {3: 15, 4: 36, 5: 36, 6: 151}, counts
    unique = {}
    for r in out:
        key = r['name']
        if key not in unique:
            unique[key] = dict(r)
            unique[key]['tables'] = str(r['table'])
        else:
            unique[key]['tables'] += ';' + str(r['table'])
            if r['alt_name']:
                unique[key]['alt_name'] = r['alt_name']
            if r['spectral_type']:
                unique[key]['spectral_type'] = r['spectral_type']
    with (BASE / 'hollands2026_exclusions_unique.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames + ['tables'])
        writer.writeheader()
        writer.writerows(sorted(unique.values(), key=lambda r: r['name']))
    metadata = dict(
        source_url=URL, source_doi='10.1093/rasti/rzag069',
        downloaded_utc_date='2026-10-18',
        html_sha256=hashlib.sha256(raw).hexdigest(),
        rows_per_table=counts, total_table_entries=len(out),
        unique_full_designations=len(unique),
        unique_name_derived_coordinate_pairs=len({(r['ra_deg'], r['dec_deg']) for r in out}),
        caution='Do not exclude only the headline green stars. Tables 3,4,5,6 all report chromaticities. Table 5 contains fitted models of actual named objects and must be excluded. Tables 1 and 2 contain generic model grids and are not object exclusions. Exact names and coordinates encode historical astrometry and must be alias/proper-motion crossmatched before any novelty claim.',
        shared_names=[dict(name=k, tables=v['tables']) for k,v in unique.items() if ';' in v['tables']],
    )
    (BASE / 'hollands2026_exclusions_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
