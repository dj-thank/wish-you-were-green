"""Reproduce the bounded literature and identity audit from downloaded sources.

Run from any working directory. This is deliberately separate from the colour
screening pipeline: existing physical properties and new colour calculations
must not be conflated. No live network requests are made by this script.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import urllib.parse

OUT = Path(__file__).resolve().parent
PAPERS = OUT / 'primary_papers'

H26 = 'https://arxiv.org/html/2610.18966v1'
H17 = 'https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/467/4970/table3.dat'
K26 = 'https://arxiv.org/abs/2606.25377'
K25 = 'https://arxiv.org/abs/2412.04611'
Z26 = 'https://doi.org/10.5281/zenodo.20775938'
V24 = 'https://arxiv.org/abs/2308.05572'
S26 = 'https://arxiv.org/html/2609.04314v1'

CANDIDATES = [
    dict(label='J0913+4434', gaia='818833831355548928', simbad='j0913',
         aliases=['WDJ091336.37+443405.41','WDJ091336.37+443405.40',
                  'SDSS J091336.38+443405.4','SDSS J091336.38+443405.3'],
         panel_pdf='kilic2026_allfitsDZ.pdf', panel_page=321,
         panel_png='kilic2026_j0913_page321.png',
         interpretation='Pale yellow-green candidate; broad depression around Na D and blue-flux suppression are reproduced qualitatively by an existing metal-polluted atmosphere model.'),
    dict(label='J1323-0129', gaia='3638333660492606976', simbad='j1323',
         aliases=['WDJ132312.76-012923.67','SDSS J132312.76-012923.8',
                  'SDSS J132312.75-012923.8'],
         panel_pdf='kilic2026_allfitsDZ.pdf', panel_page=572,
         panel_png='kilic2026_j1323_page572.png',
         interpretation='Yellow candidate with tentative DZ: classification. Atmospheric parameters differ substantially between the 2025 and 2026 fits; the spectrum-derived colour does not require choosing either parameter set.'),
    dict(label='J1329+0033', gaia='3711047662972690688', simbad='pink3711',
         aliases=['WDJ132942.69+003336.60','2QZ J132942.7+003340'],
         panel_pdf='kilic2026_allfitsDQ.pdf', panel_page=375,
         panel_png='kilic2026_j1329_page375.png',
         interpretation='Pink candidate with strong Swan-band pattern fitted by an existing DQ model. SIMBAD lists an older uncertain DA: XP classification; the DESI analysis classifies it DQ.'),
    dict(label='J1401+3903', gaia='1496016553207149952', simbad='pink1496',
         aliases=['WDJ140155.42+390326.47'],
         panel_pdf='kilic2026_allfitsDQ.pdf', panel_page=404,
         panel_png='kilic2026_j1401_page404.png',
         interpretation='Pink candidate with strong Swan-band pattern fitted by an existing DQ model; DQ classification also appears in the earlier Gaia XP catalogue.'),
    dict(label='J0429-0354', gaia='3204436719718449280', simbad='3204436719718449280',
         aliases=['WDJ042944.71-035422.00','WDJ042944.7-035422.00'],
         panel_pdf='kilic2026_allfitsDZ.pdf',panel_page=174,
         panel_png='kilic2026_j0429_page174.png',
         interpretation='Second pale-green candidate, with Gaia XP and DESI spectra and a previously published DZ atmosphere fit. No other Gaia DR3 source is catalogued within the queried10arcsec cone.'),
    dict(label='J1258+0106 / LP616-53', gaia='3690311908759604608', simbad='3690311908759604608',
         aliases=['WDJ125858.25+010632.45','LP 616-53','NLTT 32489',
                  'LSPM J1258+0106S','WDS J12589+0107B','LDS 4303B'],
         panel_pdf='kilic2026_allfitsDZ.pdf',panel_page=551,
         panel_png='kilic2026_j1258_page551.png',
         interpretation='Downgraded because of blending risk: bright visual companion LP616-54 only2.34arcsec away atJ2000, plus another Gaia entry about1.29arcsec away. This is not a clean headline green-white-dwarf result.'),
]


def decode_coord(coord):
    match = re.fullmatch(r'(\d\d)(\d\d)(\d\d\.\d+)([+-])(\d\d)(\d\d)(\d\d\.\d+)', coord)
    if not match:
        raise ValueError(coord)
    h, m, s, sign, d, dm, ds = match.groups()
    return ((int(h)+int(m)/60+float(s)/3600)*15,
            (int(d)+int(dm)/60+float(ds)/3600)*(-1 if sign=='-' else 1))


def separation(ra1, dec1, ra2, dec2):
    a, b, c, d = map(math.radians, (ra1, dec1, ra2, dec2))
    h = math.sin((d-b)/2)**2 + math.cos(b)*math.cos(d)*math.sin((c-a)/2)**2
    return math.degrees(2*math.asin(math.sqrt(min(1, max(0, h)))))*3600


def simbad_position(text):
    m = re.search(r'Coordinates\(ICRS,ep=J2000,eq=2000\):\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([+-]\d+)\s+(\d+)\s+([\d.]+)', text)
    if not m:
        raise ValueError('No SIMBAD J2000 coordinate')
    h, mi, s, d, dm, ds = m.groups()
    return ((int(h)+int(mi)/60+float(s)/3600)*15,
            (abs(int(d))+int(dm)/60+float(ds)/3600)*(-1 if d.startswith('-') else 1))


def closest(ra, dec, rows):
    return min((dict(name=name, separation_arcsec=separation(ra, dec, r, d))
                for name, r, d in rows), key=lambda x:x['separation_arcsec'])


def matched_rows(path, gaia):
    return [dict(line=i+1, row=s) for i, s in enumerate(path.read_text().splitlines())
            if gaia in s.split()]


def main():
    h26 = list(csv.DictReader((OUT/'hollands2026_exclusions_unique.csv').open()))
    h26pos = [(r['name'],float(r['ra_deg']),float(r['dec_deg'])) for r in h26]
    h17pos = [('SDSS J'+s[:18],*decode_coord(s[:18]))
              for s in (PAPERS/'hollands2017_table3.dat').read_text().splitlines()]
    evidence = []
    audit = []
    neighbourdata=json.loads((OUT/'gaia_neighbour_audit.json').read_text())
    neighbourlookup={c['gaia_source_id']:c for c in neighbourdata['candidates']}
    swandata=json.loads((OUT/'swan2026_candidate_audit.json').read_text())
    swanlookup={c['gaia_source_id']:c for c in swandata['candidates']}

    def ev(c, source, url, method, establishes, limitation):
        evidence.append(dict(candidate=c['label'],gaia_source_id=c['gaia'],
                             source=source,url=url,check=method,
                             establishes=establishes,limitation=limitation))

    for original in CANDIDATES:
        c = dict(original)
        raw = (PAPERS/('simbad_'+c['simbad']+'.txt')).read_text()
        c['simbad_url'] = 'https://simbad.cds.unistra.fr/simbad/sim-id?'+urllib.parse.urlencode(
            {'Ident':'Gaia DR3 '+c['gaia'],'output.format':'ASCII'})
        ra, dec = simbad_position(raw)
        c.update(ra_deg=ra,dec_deg=dec,coordinate_frame='ICRS',coordinate_epoch='J2000')
        bib = raw.split('Bibcodes',1)[1].split('Measures',1)[0]
        c['simbad_bibcodes'] = re.findall(r'\b\d{4}[A-Za-z&.]+\d[A-Za-z\d.]*[A-Za-z]\b',bib)
        c['nearest_hollands2026'] = closest(ra,dec,h26pos)
        c['nearest_hollands2017'] = closest(ra,dec,h17pos)
        c['kilic2026_table_rows'] = matched_rows(PAPERS/'kilic2026_table1.txt',c['gaia'])
        c['kilic2025_table_rows'] = matched_rows(PAPERS/'kilic2025_Table2_ALL.txt',c['gaia'])
        c['known_star'] = True
        c['potentially_new_quantity'] = 'CIE human-vision chromaticity and robustness analysis of these public spectra'
        c['global_priority_verified'] = False
        if c['gaia'] in neighbourlookup:
            c['gaia_neighbour_audit']=neighbourlookup[c['gaia']]
        c['swan2026_audit']=swanlookup[c['gaia']]['summary']
        audit.append(c)
        ev(c,'SIMBAD object record',c['simbad_url'],
           'Read Gaia-ID-resolved identity, epoch-labelled position, aliases and bibliography.',
           'The astronomical object is already catalogued; aliases resolve to the same star.',
           'SIMBAD bibliography is not complete or instantaneous; Kilic2026 is absent from these records despite the source table containing the stars.')
        near=c['nearest_hollands2026']
        ev(c,'Hollands2026 Tables3-6',H26,
           'Compared SIMBAD J2000 coordinates against all236 unique named entries parsed from Tables3-6; nearest '+near['name']+' at '+format(near['separation_arcsec'],'.3f')+'arcsec.',
           'This object is absent from the named object tables of the comparison paper.',
           'The encoded coordinates of the comparison tables have no explicitly resolved epoch. Separations of more than one degree make ordinary proper-motion or short-alias confusion immaterial here; absence from one paper does not establish worldwide novelty.')
        near=c['nearest_hollands2017']
        ev(c,'Hollands2017 full231 DZ parent catalogue',H17,
           'Compared against every fixed-width designation in CDS table3.dat; nearest '+near['name']+' at '+format(near['separation_arcsec'],'.3f')+'arcsec.',
           'No hidden match to the larger2017 DZ parent catalogue.',
           'This is an identity exclusion, not proof that no other paper measured perceived colour.')
        ev(c,'Kilic2026 source table1',K26,
           'Exact GaiaID match in the authors machine-readable table1.txt: '+c['kilic2026_table_rows'][0]['row'],
           'The spectrum classification and atmospheric parameters are prior published analysis.',
           'These physical measurements are not new results of this colour search. The metal analysis fixes other heavy-element ratios to CI chondrites rather than fitting individual Na abundances.')
        ev(c,'Kilic2026 public model-fit figures',Z26,
           c['panel_pdf']+' page'+str(c['panel_page'])+' (one-based), rendered and visually inspected; identifier matches the candidate.',
           'A previously computed stellar-atmosphere model accounts qualitatively for the broad absorption features.',
           'The plotted spectra are F_nu. Visual agreement is not a new quantitative atmospheric fit or independent observation; the raw DESI spectrum is the same observation as used by the colour analysis.')
        if c['kilic2025_table_rows']:
            ev(c,'Kilic2025 table2',K25,
               'Exact GaiaID match: '+c['kilic2025_table_rows'][0]['row'],
               'An earlier tentative DZ classification and physical fit already existed.',
               'The large2025-to2026 parameter change shows model dependence; formal fit errors do not encompass that systematic difference.')
        ev(c,'Relevant survey full texts',K26+' ; '+V24+' ; '+K25,
           'Read classification/parameterisation methods and searched full authors source texts; colour is used for passband indices or plotting symbols, with no CIE/chromaticity/sRGB/perceived-colour quantities found.',
           'The inspected surveys are prior physical/spectral work and do not themselves supply the human-colour quantity being calculated here.',
           'This conclusion is bounded to the retrieved texts and supplements checked. It cannot exclude an overlooked paper, unpublished analysis or unindexed supplement.')
        swan=swanlookup[c['gaia']]
        ev(c,'Swan2026 DESI DR1 white dwarf catalogue',S26,
           'Exact Gaia-ID match in the official version1.0 catalogue and WDJname join to external-data and exposure tables: '+json.dumps(swan['summary'])+'. Sections6.6 and7.8.7 read; full text searched for CIE/chromaticity/sRGB/perceived/pink/human eye with no matches; green occurrences are image channels or author names.',
           'The object and its spectral class are prior work. The catalogue supplies an exposure-weighted neighbouring-light estimate; it does not report the human-colour quantity calculated in this search.',
           'Flux ratios mean neighbour flux divided by target flux, not total flux. They assume Gaia-listed sources and Gaussian PSFs and are not upper bounds. PSF wings, unlisted sources and instrumental cross-talk may escape this metric. Gaia BP/RP aperture modelling is approximate; catalogued coadd masking is not necessarily the mask of an individual MWDD spectrum. Absence of human-colour quantities from this paper is not proof of worldwide priority.')
        if c['gaia'] in neighbourlookup:
            n=neighbourlookup[c['gaia']]
            neighbours=[r for r in n['rows'] if r['Source']!=c['gaia']]
            ev(c,'Gaia DR3 local field and photometry quality',n['source_url'],
               'Queried10arcsec cone in catalogueI/355/gaiadr3; '+str(n['neighbour_count'])+'other catalogued sources. Neighbour data: '+json.dumps(neighbours),
               'Identifies catalogued nearby light sources and Gaia blended-transit flags relevant to colour validation.',
               n['limitation'])
        if c['gaia']=='3690311908759604608':
            ev(c,'SIMBAD visual-double companion identity',
               'https://simbad.cds.unistra.fr/simbad/sim-id?Ident=LDS+4303A&output.format=ASCII',
               'ResolvedLDS4303A toLP616-54 and computed2.340033751arcsec J2000 separation; companionGaiaG17.252741 vs target18.404011.',
               'A brighter close companion provides a concrete reason to downgrade the colour candidate pending deblending analysis.',
               'No stellar-light decontamination or orbit fit was performed; this does not prove all of the measured green tint is an artefact.')

    textaudit={}
    for filename in ['kilic2020_ms.tex','kilic2025_ms.tex','kilic2026_ms.tex','vincent2023_ms.tex','vincent2024_aanda.tex','swan2026_text.txt']:
        s=(PAPERS/filename).read_text()
        terms=['CIE','chromaticity','chromaticities','sRGB','perceived','pink','green','naked eye','human eye']
        textaudit[filename] = dict(
            word_counts={term:len(re.findall(r'\b'+re.escape(term)+r'\b',s,re.I)) for term in terms},
            green_contexts=[dict(line=i+1,text=line) for i,line in enumerate(s.splitlines()) if re.search(r'\bgreen\b',line,re.I)],
            interpretation='Whole-word matching avoids counting CIE inside words such as efficiency. Green occurrences were checked and are author/survey names or plotting colours, not perceived stellar-colour measurements.')
    metadata=dict(audit_date='2026-10-18',comparison_named_unique_objects=len(h26pos),
                  comparison_parent_dz_objects=len(h17pos),
                  conclusion='New reproducible colour analysis of known stars, with candidates absent from all named comparison-paper tables. Global scientific priority remains provisional.',
                  coordinate_note='Candidate positions independently resolved by SIMBAD to J2000 ICRS; no epoch is invented for coordinate-encoded exclusion names.',
                  sodium_followup_caution=swandata['sodium_followup_caution'],
                  candidates=audit,full_text_checks=textaudit)
    (OUT/'candidate_novelty_audit.json').write_text(json.dumps(metadata,indent=2))
    with (OUT/'novelty_evidence.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(evidence[0]));writer.writeheader();writer.writerows(evidence)
    sourcefiles=[OUT/'hollands2026.html',OUT/'hollands2026_exclusions_unique.csv']+list(OUT.glob('candidate_*.html'))+[
        p for p in PAPERS.iterdir() if p.suffix in ['.tex','.dat','.txt','.json','.pdf','.tsv','.gz'] or p.name.endswith('ReadMe') or p.name=='swan2026.html']
    manifest=[dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
              for p in sorted(sourcefiles)]
    (OUT/'novelty_source_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'candidates':len(audit),'evidence_rows':len(evidence),'sources_hashed':len(manifest)},indent=2))


if __name__=='__main__':
    main()
