"""Extract candidate-level contamination estimates from Swan et al. (2026).

Inputs are the authors' unchanged gzip CSV tables downloaded on 2026-10-18.
Gaia identifiers remain strings throughout. No network access or atmosphere
modelling occurs here. These contamination estimates apply the authors' model,
not an independently measured or rigorous upper bound on contaminating flux.
"""
from pathlib import Path
import csv
import gzip
import hashlib
import json

OUT = Path(__file__).resolve().parent
RAW = OUT / 'primary_papers'
BASE = 'https://cygnus.astro.warwick.ac.uk/phsdaj/WhiteDwarfs/Tables/'
PAPER = 'https://arxiv.org/html/2609.04314v1'
TARGETS = {
    '818833831355548928': 'J0913+4434',
    '3204436719718449280': 'J0429-0354',
    '3711047662972690688': 'J1329+0033',
    '3638333660492606976': 'J1323-0129',
    '3690311908759604608': 'J1258+0106 / LP616-53',
    '1496016553207149952': 'J1401+3903',
}
FILES = {
    'catalogue': 'DESI_DR1_catalogue_1.0.csv.gz',
    'external_data': 'DESI_DR1_externalData_1.0.csv.gz',
    'exposures': 'DESI_DR1_exposures_1.0.csv.gz',
}


def read_rows(filename):
    with gzip.open(RAW / filename, 'rt', newline='') as f:
        yield from csv.DictReader(f)


def main():
    candidates = []
    for row in read_rows(FILES['catalogue']):
        gaia = row['designation'].rsplit(' ', 1)[-1]
        if gaia in TARGETS:
            candidates.append(dict(
                label=TARGETS[gaia], gaia_source_id=gaia,
                WDJname=row['WDJname'], catalogue_raw=row,
                external_data_raw=None, exposures_raw=[]))
    assert len(candidates) == len(TARGETS)
    assert len({c['gaia_source_id'] for c in candidates}) == len(TARGETS)
    by_name = {c['WDJname']: c for c in candidates}
    for row in read_rows(FILES['external_data']):
        if row['WDJname'] in by_name:
            assert by_name[row['WDJname']]['external_data_raw'] is None
            by_name[row['WDJname']]['external_data_raw'] = row
    for row in read_rows(FILES['exposures']):
        if row['WDJname'] in by_name:
            by_name[row['WDJname']]['exposures_raw'].append(row)

    summary = []
    for c in candidates:
        cat, ext, exps = c['catalogue_raw'], c['external_data_raw'], c['exposures_raw']
        assert ext is not None
        assert len(exps) == int(cat['nExposures'])
        row = dict(label=c['label'], gaia_source_id=c['gaia_source_id'],
                   WDJname=c['WDJname'], swan_specType=cat['specType'],
                   swan_specType_confidence=float(cat['specType_confidence']),
                   nExposures=int(cat['nExposures']),
                   nNeighbours_DESI=int(cat['nNeighbours_DESI']))
        row['neighbour_to_target_flux_DESI'] = float(cat['fluxContamination_DESI'])
        for key in ['PanSTARRS', 'SDSS', 'Gaia_G', 'Gaia_BPRP']:
            row['neighbour_to_target_flux_' + key] = float(ext['fluxContamination_' + key])
        row['exposure_seeing_arcsec'] = ';'.join(e['SEEING_GFA'] for e in exps)
        row['exposure_MJD'] = ';'.join(e['MJD'] for e in exps)
        row['exposure_ids'] = ';'.join(e['EXPOSURE'] for e in exps)
        row['catalogue_fractionMasked_Z'] = float(cat['fractionMasked_Z'])
        summary.append(row)
        c['summary'] = row

    result = dict(
        audit_date='2026-10-18', paper_url=PAPER,
        title='The DESI Data Release 1 white dwarf catalogue',
        table_version='1.0',
        contamination_definition='Neighbour flux entering the aperture divided by target flux entering the aperture; not neighbour flux divided by total flux.',
        method='Swan et al. section 6.6: Gaia DR2/DR3 neighbours within 60 arcsec, proper-motion propagation to each exposure, 0.75 arcsec fibre radius, Gaussian PSF from measured seeing, Gaia G flux ratio, effective-exposure-time weighting. Photometric aperture estimates use fixed survey epochs and assumed Gaussian PSFs.',
        limitations=[
            'Values are model estimates, not observational error bars or rigorous upper bounds.',
            'The Gaussian approximation omits PSF wings, diffraction spikes and scattering; unlisted sources and spectrograph fibre-to-fibre cross-talk may escape the metric.',
            'Gaia BP/RP contamination is a rough circular-aperture approximation to dispersed spectra measured at many scan angles, with pipeline deblending.',
            'The catalogue may combine exposures. An exposure-specific MWDD spectrum can differ from the catalogue coadd, so catalogue mask fractions must not be substituted for the actual analysed spectrum mask.',
            'The published H/He atmosphere model parameters are not used to infer human colour; the catalogue warns that metal- or carbon-bearing atmospheres require appropriate specialised models.',
        ],
        sodium_followup_caution='Section 7.8.7 reports broad Na-D-like DESI absorption confirmed by X-Shooter in WDJ034301.05-011401.58 but not in WDJ220022.42-061430.97. The latter feature occurred in consecutive DESI exposures; its origin remained unresolved. Repeat spectra from the same instrumental setup are therefore insufficient by themselves to prove intrinsic photospheric absorption.',
        identity_and_priority='All six exact Gaia IDs were already classified in Swan2026. The inspected paper reports no CIE/chromaticity/sRGB/perceived-colour measurements. This bounds the comparison with that paper and does not establish worldwide priority.',
        sources=[dict(name=k, filename=v, url=BASE+v,
                      bytes=(RAW/v).stat().st_size,
                      sha256=hashlib.sha256((RAW/v).read_bytes()).hexdigest())
                 for k,v in FILES.items()],
        candidates=candidates)
    (OUT/'swan2026_candidate_audit.json').write_text(json.dumps(result, indent=2))
    with (OUT/'swan2026_candidate_contamination.csv').open('w', newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
