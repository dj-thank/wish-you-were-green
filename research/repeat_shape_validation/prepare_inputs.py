#!/usr/bin/env python3
"""Freeze the existing repeated-observation evidence; no network requests."""
from __future__ import annotations
import csv
import gzip
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from astropy.io import fits
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    source = ROOT / 'research/literature/sources'
    manifest_path = source / 'desi_additional_nights_manifest.json'
    initial = json.loads(manifest_path.read_text())
    prior_path = source / 'candidate27_prior_rows.json'
    prior = json.loads(prior_path.read_text())['candidates']
    inputs = HERE / 'inputs'
    inputs.mkdir(exist_ok=True)
    pairs = []
    for sid in dict.fromkeys(e['gaia_source_id'] for e in initial['epochs']):
        epochs = []
        for e in initial['epochs']:
            if e['gaia_source_id'] != sid:
                continue
            p = ROOT / 'research/literature' / e['selected_rows_path']
            assert sha(p) == e['selected_rows_sha256']
            inv = e['exposure_inventory']
            epochs.append(dict(path=str(p.relative_to(ROOT)), sha256=sha(p),
                night=inv['NIGHT'], exposure=str(inv['EXPOSURE']),
                targetid=inv['TARGETID'], fiber=inv['FIBER'], observed_mjd=float(inv['MJD']),
                metadata=e))
        photo = prior[sid]['swan_external'][0]
        pairs.append(dict(pair_id='desi_'+sid, source_id=sid, label=next(x['label'] for x in initial['epochs'] if x['gaia_source_id']==sid),
            instrument='DESI', epochs=epochs, selection='Existing highest published SN_R exposure per usable night; selected before this shape analysis',
            calibration_system='panstarrs', observed_gri=[float(photo[f'Pan-STARRS.{b}']) for b in 'gri'],
            observed_gri_errors=[float(photo[f'Pan-STARRS.{b}_error']) for b in 'gri'],
            photometry_identity='Same Swan externalData_1.0 PS1 mean-PSF anchors for both nights',
            observed_griz=[float(photo[f'Pan-STARRS.{b}']) for b in 'griz'],
            observed_griz_errors=[float(photo[f'Pan-STARRS.{b}_error']) for b in 'griz']))
    epochs = []
    extra_manifests = []
    for name in ['j1329_desi_20220127_swan_manifest.json', 'j1329_desi_20220311_manifest.json']:
        mp=source/name
        e=json.loads(mp.read_text())
        p=ROOT/'research/literature'/e['selected_rows_path']
        assert sha(p)==e['selected_rows_sha256']
        if 'NIGHT' in e:
            night, expid, fiber=e['NIGHT'],e['EXPID'],e['FIBER']
        else:
            night, expid, fiber=e['files'][0]['NIGHT'],e['files'][0]['EXPID'],e['files'][0]['fiber']
        epochs.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),night=str(night),exposure=str(expid),fiber=str(fiber),targetid=e['desi_targetid'],metadata=e))
        extra_manifests.append(mp)
    pairs.append(dict(pair_id='desi_3711047662972690688',source_id='3711047662972690688',label='J1329+0033',instrument='DESI',epochs=epochs,
        selection='Existing two distinct nights, retained despite the second Z arm being entirely invalid',
        calibration_system=None,observed_gri=None,observed_gri_errors=None,
        photometry_identity='Full gri/griz unavailable on common B/R support; no extrapolation or anchor correction'))
    screen_path=ROOT/'research/precision/flux_units/corrected_record_screen.csv.gz'
    with gzip.open(screen_path,'rt') as h:
        records={r['row_index']:r for r in csv.DictReader(h) if r['row_index'] in ['9667','9677']}
    sdss_manifest_path=ROOT/'sdss/manifest_with_photometry.json.gz'
    sdss_records=json.loads(gzip.open(sdss_manifest_path,'rt').read())
    epochs=[]
    phot=[]
    for index in ['9667','9677']:
        r=records[index]
        assert r['flux_units_validated']=='True' and r['flux_input_convention']=='flambda' and r['usable_screen']=='True'
        p=ROOT/r['raw_path'];raw=p.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==r['sha256']
        copy=inputs/(p.name+'.gz')
        copy.write_bytes(gzip.compress(raw,mtime=0))
        with fits.open(io.BytesIO(raw)) as h:
            hdr=h[0].header
            meta={k:hdr.get(k) for k in ['PLATEID','MJD','MJDLIST','FIBERID','PLUG_RA','PLUG_DEC','BUNIT','EXPTIME','NEXP']}
            meta['science_exposure_ids']=sorted({int(hdr[k].split('-')[1]) for k in hdr if k.startswith('EXPID')})
            assert meta['BUNIT']=='1E-17 erg/cm^2/s/Ang'
        m=next(x for x in sdss_records if x['spectrum_id']==r['spectrum_id'])
        epochs.append(dict(path=str(copy.relative_to(ROOT)),sha256=sha(copy),uncompressed_sha256=r['sha256'],
            original_path=r['raw_path'],original_url=r['source_url'],retrieved_utc=m.get('retrieved_utc'),
            night=str(meta['MJD']),observed_mjd=meta['MJD'],exposure=r['spectrum_id'],fiber=str(meta['FIBERID']),
            contributing_mjds=[int(x) for x in meta['MJDLIST'].split()],
            row_index=int(index),metadata=meta,unit_gate={k:r[k] for k in ['row_index','source_id','flux_units_validated','flux_input_convention','usable_screen','identity_basis']}))
        phot.append(m)
    assert phot[0]['photometry_objid']==phot[1]['photometry_objid']
    for b in 'gri':
        assert phot[0][b+'_psf_flux_nanomaggies']==phot[1][b+'_psf_flux_nanomaggies']
        assert phot[0][b+'_psf_mag_err']==phot[1][b+'_psf_mag_err']
    pairs.append(dict(pair_id='sdss_3646912496889350784',source_id='3646912496889350784',label='J1410-0235',instrument='SDSS',epochs=epochs,
        selection='Purposive follow-up of previously visually flagged rows 9667/9677; two different plate/MJD/fibre coadds with disjoint sets of five observing nights and 18 physical exposures, not two single-night spectra or duplicate representations',
        calibration_system='sdss',observed_gri=[22.5-2.5*np.log10(phot[0][b+'_psf_flux_nanomaggies']) for b in 'gri'],
        observed_gri_errors=[phot[0][b+'_psf_mag_err'] for b in 'gri'],
        photometry_identity='Identical SDSS photometry objID '+str(phot[0]['photometry_objid'])+' and PSFFLUX values in both original HDU2 records',
        shared_photometry_records=phot))
    sources=[manifest_path,prior_path,screen_path,sdss_manifest_path,*extra_manifests]
    out=dict(created_utc=datetime.now(timezone.utc).isoformat(),pairs=pairs,
        source_manifest_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},
        references=[
            'https://desidatamodel.readthedocs.io/en/latest/DESI_SPECTRO_REDUX/SPECPROD/exposures/NIGHT/EXPID/cframe-CAMERA-EXPID.html',
            'https://data.sdss.org/datamodel/files/BOSS_SPECTRO_REDUX/RUN2D/spectra/lite/PLATE4/spec.html',
            'https://speclite.readthedocs.io/en/latest/api/speclite.filters.FilterResponse.html'],
        limits=['The core SDSS Gaia association remains a legacy positional association; the two FITS target the same PLUG coordinates. Separate exposure-epoch Gaia point-estimate checks are documented in sdss_context.json and do not replace the core identity pipeline.',
                'Two headline targets J0429-0354 and J0913+4434 have only one exposure each in the frozen candidate inventory. These other objects do not measure their repeatability.',
                'No survey-wide random or complete repeated-observation sample is constructed.'])
    (HERE/'inputs_manifest.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'pairs':len(pairs),'distinct_DESI_exposures':8,'SDSS_observations':2,'copied_raw_SDSS_bytes':sum(p.stat().st_size for p in inputs.glob('*.gz'))}))


if __name__=='__main__':main()
