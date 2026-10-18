#!/usr/bin/env python3
"""Select published Q/Z-type white-dwarf spectra plus colour-spanning controls."""
from pathlib import Path
import json
import math
from collections import Counter
import numpy as np
from astropy.table import Table

BASE = Path(__file__).resolve().parent

def number(value):
    if np.ma.is_masked(value):
        return None
    f = float(value)
    return f if math.isfinite(f) else None

def coordinates(name):
    ra = 15 * (int(name[:2]) + int(name[2:4])/60 + float(name[4:9])/3600)
    dec = int(name[10:12]) + int(name[12:14])/60 + float(name[14:])/3600
    return ra, (-dec if name[9] == '-' else dec)

def convert(row, index):
    name = str(row['SDSSJ']).strip()
    plate, mjd, fiber = (int(x) for x in str(row['P-M-F']).strip().split('-'))
    ra, dec = coordinates(name)
    result = dict(name='SDSS J'+name, sdss_name=name, ra=ra, dec=dec,
                  type=str(row['Type']).strip(), plate=plate, mjd=mjd, fiber=fiber,
                  snrg=number(row['SNg']), catalogue_row=index+1,
                  catalogue='Kepler et al. 2019, MNRAS 486, 2169',
                  catalogue_url='https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/486/2169/',
                  catalogue_doi='10.26093/cds/vizier.74862169',
                  ebv=number(row['E(B-V)']), pm_mas_yr=number(row['PM']))
    result['spectrum_id'] = f'{plate:04d}-{mjd:05d}-{fiber:04d}'
    for band in 'ugriz':
        result[band] = number(row[band+'mag'])
        result[band+'_err'] = number(row['e_'+band+'mag'])
    return result

if __name__ == '__main__':
    cat = BASE / 'catalogues'
    table = Table.read(cat/'table2.dat', format='ascii.cds', readme=str(cat/'ReadMe'))
    all_rows = [convert(row, i) for i, row in enumerate(table)]
    selected = [r for r in all_rows if r['type'].startswith('D') and
                ('Q' in r['type'] or 'Z' in r['type'])]
    for row in selected:
        row['selection_group'] = 'published_Q_or_Z_type'
    selected.sort(key=lambda r: (
        0 if r['type'].startswith('DZ') else 1 if r['type'].startswith('DQ') else 2,
        -(r['snrg'] or 0), r['spectrum_id']))
    for kind in ['DA', 'DC', 'DB']:
        controls = [r for r in all_rows if r['type'] == kind and (r['snrg'] or 0) >= 20
                    and all(r[k] is not None and r[k] > 0 for k in ['g','r','g_err','r_err'])]
        controls.sort(key=lambda r: r['g']-r['r'])
        for index in np.linspace(0, len(controls)-1, 18, dtype=int):
            row = controls[index].copy()
            row['selection_group'] = 'control_'+kind
            selected.append(row)
    # One entry per observation; the parent analysis must deduplicate sky objects.
    unique = {r['spectrum_id']:r for r in selected}
    selected = list(unique.values())
    (BASE/'targets.json').write_text(json.dumps(selected, indent=2))
    import pandas as pd
    pd.DataFrame(selected).to_csv(BASE/'targets.csv', index=False)
    report = dict(catalogue_rows=len(table), selected_spectra=len(selected),
                  selected_type_counts=dict(Counter(r['type'] for r in selected)),
                  group_counts=dict(Counter(r['selection_group'] for r in selected)),
                  selection='All Type beginning D and containing Q or Z, plus 18 high-S/N colour-spanning DA/DC/DB controls each. No novelty assertion.')
    (BASE/'selection_report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
