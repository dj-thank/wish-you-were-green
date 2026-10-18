"""Summarise saved Gaia DR3 10-arcsecond cone queries without losing ID precision."""
from pathlib import Path
import csv
import io
import json
import math
import urllib.parse

OUT = Path(__file__).resolve().parent
PAPERS = OUT/'primary_papers'
TARGETS = [
    ('j0429','3204436719718449280',67.4362916667,-3.90650555556),
    ('j0913','818833831355548928',138.4020833333,44.5681305556),
    ('j1329','3711047662972690688',202.4277,.55964),
    ('j1323','3638333660492606976',200.8030833333,-1.490425),
    ('j1258','3690311908759604608',194.743208333,1.10759722222),
]


def sep(ra1,dec1,ra2,dec2):
    a,b,c,d=map(math.radians,(ra1,dec1,ra2,dec2))
    h=math.sin((d-b)/2)**2+math.cos(b)*math.cos(d)*math.sin((c-a)/2)**2
    return math.degrees(2*math.asin(math.sqrt(h)))*3600


def main():
    out=[]
    keys=['Source','RA_ICRS','DE_ICRS','Gmag','BPmag','RPmag','Plx','RUWE',
          'IPDfmp','IPDfow','Dup','o_BPmag','NBPcont','NBPblend',
          'o_RPmag','NRPcont','NRPblend']
    for label,sourceid,ra,dec in TARGETS:
        filename='gaia10arcsec_'+label+'.tsv'
        lines=[s for s in (PAPERS/filename).read_text().splitlines() if s and not s.startswith('#')]
        data=list(csv.DictReader(io.StringIO('\n'.join(lines)),delimiter='\t'))[2:]
        rows=[{k:r[k].strip() for k in keys} for r in data]
        target=next(r for r in rows if r['Source']==sourceid)
        for r in rows:
            r['separation_from_target_arcsec']=sep(float(target['RA_ICRS']),float(target['DE_ICRS']),float(r['RA_ICRS']),float(r['DE_ICRS']))
            r['G_flux_relative_to_target']=10**(.4*(float(target['Gmag'])-float(r['Gmag'])))
        url='https://vizier.cds.unistra.fr/viz-bin/asu-tsv?'+urllib.parse.urlencode({
            '-source':'I/355/gaiadr3','-c':f'{ra} {dec}','-c.rs':'10','-out.all':'1','-out.max':'100'})
        out.append(dict(label=label,gaia_source_id=sourceid,source_url=url,
            source_file='primary_papers/'+filename,catalogue='Gaia DR3 I/355/gaiadr3',
            astrometric_epoch=2016.0,query_radius_arcsec=10,rows=rows,
            neighbour_count=len(rows)-1,
            limitation='Only catalogued Gaia DR3 sources in this cone are covered. No absence of unresolved companions, galaxies or fainter sources is inferred. Blended-transit counts are quality flags, not a measured contamination fraction.'))
    result=dict(audit_date='2026-10-18',candidates=out)
    (OUT/'gaia_neighbour_audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps([{k:c[k] for k in ['label','gaia_source_id','neighbour_count']} for c in out],indent=2))


if __name__=='__main__':main()
