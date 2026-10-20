#!/usr/bin/env python3
"""Independent layers for J1323: unit identity, fibre association and colour.

The newly identified SDSS FITS and the MWDD SDSS export are representations of
one observation. Their agreement is never counted as an independent repeat.
The existing calibration policy is replayed without changing frozen screens.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import warnings

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'j1323'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'mpl-cache'))
import numpy as np
import pandas as pd
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from erfa import ErfaWarning
import colour_pipeline as c
from flux_conventions import as_flux_lambda
from fetch_and_identify import inputs, parse_original, native

SOURCE_ID = '3638333660492606976'
REF = 'sdss_dr17_v5_13_2_4049_55591_0832'
MASK_NAMES = {16: 'NEARBADPIXEL', 17: 'LOWFLAT', 18: 'FULLREJECT',
              19: 'PARTIALREJECT', 22: 'NOSKY', 23: 'BRIGHTSKY',
              24: 'NODATA', 25: 'COMBINEREJ', 26: 'BADFLUXFACTOR',
              27: 'BADSKYCHI'}
DOCS = {
    'spectra_and_units': 'https://www.sdss4.org/dr17/spectro/spectro_basics/',
    'pixel_mask_definitions': 'https://www.sdss4.org/dr17/algorithms/bitmasks/',
    'spectroscopic_caveats': 'https://www.sdss4.org/dr17/spectro/caveats/',
}


def sha(blob): return hashlib.sha256(blob).hexdigest()


def jsonable(value):
    if isinstance(value, dict): return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [jsonable(v) for v in value]
    if isinstance(value, np.ndarray): return jsonable(value.tolist())
    if isinstance(value, np.generic): return jsonable(value.item())
    if isinstance(value, float) and not np.isfinite(value): return None
    return value


def stage():
    OUT.mkdir(exist_ok=True)
    root = OUT.parent
    retrieval = json.loads((root / 'retrieval_priority.json').read_text())
    bykey = {r['key']: r for r in retrieval['records']}
    frozen = inputs()
    jobs = [bykey['mwdd_13'], bykey[REF], {
        'key': 'mwdd_14', 'format': 'mwdd', 'source_url': frozen[14][1]['source_url'],
        'sha256': frozen[14][1]['sha256'], 'raw_path': str(Path('..') / '..' / frozen[14][1]['raw_path'])}]
    original_paths = [root / jobs[0]['raw_path'], root / jobs[1]['raw_path'], ROOT / frozen[14][1]['raw_path']]
    records = []
    for job, path in zip(jobs, original_paths):
        blob = path.read_bytes()
        assert sha(blob) == job['sha256'], 'Original source changed'
        suffix = '.fits.gz' if job['format'] == 'sdss' else '.csv.gz'
        destination = OUT / (job['key'] + suffix)
        destination.write_bytes(gzip.compress(blob, mtime=0))
        records.append({**job, 'bundled_file': destination.name, 'bundled_sha256': sha(destination.read_bytes())})
    source_gaia = ROOT / 'research/external_validation/raw/gaia_dr3_extended_targets.csv'
    manifest = {'source_id': SOURCE_ID, 'records': records,
                'gaia_input_path': str(source_gaia.relative_to(ROOT)),
                'gaia_input_sha256': sha(source_gaia.read_bytes()),
                'frozen_input_sha256': sha((ROOT / 'results/screen_input_mwdd.json.gz').read_bytes()),
                'interpretation': 'Lossless copies of three exact original files. No new photometry, fitting to another spectrum, or mutation of the old unit registry.'}
    (OUT / 'input_manifest.json').write_text(json.dumps(jsonable(manifest), indent=2) + '\n')


def transformed(arrays, cal):
    w, f, iv = arrays
    fac = 10**(-.4*(cal['cal_offset_mag'] + cal['cal_tilt_mag_per_1000A']*(w-6200)/1000))
    return w, f*fac, None if iv is None else iv/fac**2


def calibration(arrays, record, only_system=None):
    w, f, _ = arrays
    decisions = []
    phot = record['photometry']
    systems = [('sdss', 's', 'Ds'), ('panstarrs', 'PS_', 'DPS_')]
    for system, prefix, eprefix in systems:
        if only_system and system != only_system: continue
        obs = [float(phot.get(prefix+b, np.nan)) for b in 'gri']
        err = [float(phot.get(eprefix+b, np.nan)) for b in 'gri']
        entry = {'system': system, 'observed_gri': obs, 'errors_gri': err}
        if not np.all(np.isfinite(obs)):
            entry['decision'] = 'unavailable'
        else:
            try:
                _, cal = c.recalibrate_gri(w, f, obs, err, system)
                accepted = cal['cal_max_residual_mag'] < .15 and abs(cal['cal_tilt_mag_per_1000A']) < .25
                entry.update(fit=cal, decision='accepted' if accepted else 'rejected_by_existing_policy')
                decisions.append(entry)
                if accepted: return transformed(arrays, cal), cal, decisions
                continue
            except ValueError as exc:
                entry.update(decision='unavailable', error=str(exc))
        decisions.append(entry)
    return arrays, None, decisions


def measure(arrays):
    w, f, iv = arrays
    m = c.integrate_colour(w, f, iv, mask_sky=True)
    m['pipeline_coverage_gate'] = bool(m['coverage_eligible'] and m['cmf_min_coverage'] > .995 and m['largest_visible_gap_A'] < 150)
    if iv is not None:
        s = np.isfinite(w) & np.isfinite(f) & np.isfinite(iv) & (iv > 0) & (w > 4000) & (w < 7500)
        m['visible_median_pixel_snr'] = float(np.median(f[s]*np.sqrt(iv[s])))
    return m


def binned(arrays, width=20, normalizer=None):
    w, f, iv = c.clean_spectrum(*arrays, mask_sky=True)
    anchor = float(np.median(f[(w >= 5200) & (w <= 5500)])) if normalizer is None else normalizer
    if not anchor > 0: raise ValueError('Nonpositive plot normalization')
    edges = np.arange(3600, 8300+width, width)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = (w >= lo) & (w < hi)
        n = int(s.sum())
        mean = float(f[s].mean()/anchor) if n else np.nan
        err = float(np.sqrt(np.sum(1/iv[s]))/n/anchor) if n and iv is not None else np.nan
        out.append(((lo+hi)/20, mean, err, n))
    return np.asarray(out), anchor


def compute(root=ROOT, folder=OUT):
    root, folder = Path(root), Path(folder)
    manifest = json.loads((folder / 'input_manifest.json').read_text())
    assert sha((root / manifest['gaia_input_path']).read_bytes()) == manifest['gaia_input_sha256']
    assert sha((root / 'results/screen_input_mwdd.json.gz').read_bytes()) == manifest['frozen_input_sha256']
    with gzip.open(root / 'results/screen_input_mwdd.json.gz', 'rt') as stream: frozen = json.load(stream)
    raws, blobs = {}, {}
    for job in manifest['records']:
        compressed = (folder / job['bundled_file']).read_bytes()
        assert sha(compressed) == job['bundled_sha256']
        blob = gzip.decompress(compressed)
        assert sha(blob) == job['sha256']
        raws[job['key']] = parse_original(blob, job); blobs[job['key']] = blob
    jobs = {r['key']: r for r in manifest['records']}
    identity = native.compare({'row_index': 13, 'entity_id': 'gaia:'+SOURCE_ID,
        'wdid': frozen[13]['wdid'], 'source_url': frozen[13]['source_url'], 'sha256': frozen[13]['sha256']},
        {'row_index': -1, 'source_url': jobs[REF]['source_url'], 'sha256': jobs[REF]['sha256']},
        raws['mwdd_13'], raws[REF])
    assert identity['convention'] == 'flambda'
    identity.update(direct_row_index=None, external_reference_id=REF)
    # Require the exact retained numeric values as well as exact source bytes.
    for i in [13, 14]:
        raw = raws[f'mwdd_{i}']
        assert sha(np.column_stack([raw['wave'], raw['flux']]).astype('<f8').tobytes()) == frozen[i]['numeric_sha256_wavelength_flux']
    arrays = {key: (r['wave'], r['flux'], r['ivar']) for key, r in raws.items()}
    # DESI follows the existing independently documented F_lambda contract.
    wd, fd, ivd = arrays['mwdd_14']
    fd, ivd, desi_units = as_flux_lambda(wd, fd, ivd, frozen[14])
    arrays['mwdd_14'] = wd, fd, ivd
    with fits.open(io.BytesIO(blobs[REF])) as hd:
        d = hd[1].data
        amask, omask = np.asarray(d['and_mask'], np.uint32), np.asarray(d['or_mask'], np.uint32)
        h0 = {k: hd[0].header.get(k) for k in ['BUNIT', 'PLATEID', 'MJD', 'FIBERID', 'RUN2D', 'PLUG_RA', 'PLUG_DEC', 'VACUUM', 'EXPTIME', 'NEXP']}
        keys = ['CLASS', 'SUBCLASS', 'Z', 'ZWARNING', 'SN_MEDIAN_ALL', 'PLATEQUALITY', 'SPECOBJID', 'OBJID', 'PSFMAG', 'PSFMAGERR', 'PSFFLUX', 'PSFFLUX_IVAR']
        h2 = {k: hd[2].data[k][0] for k in keys if k in hd[2].data.names}
    w, f, iv = arrays[REF]
    visible = (w >= 3600) & (w <= 8300)
    mask_counts = {}
    for name, masks in [('AND', amask), ('OR', omask)]:
        mask_counts[name] = {'any_flagged_all': int((masks != 0).sum()),
            'any_flagged_visible': int((visible & (masks != 0)).sum()),
            'visible_bit_counts': {str(bit): {'name': MASK_NAMES.get(bit, 'see_official_mask_dictionary'),
                'count': int((visible & ((masks & (1 << bit)) != 0)).sum())} for bit in range(32) if (visible & ((masks & (1 << bit)) != 0)).any()}}
    quality = {'native_samples': len(w), 'native_visible_samples': int(visible.sum()),
        'inverse_variance_nonpositive_all': int((iv <= 0).sum()),
        'inverse_variance_nonpositive_visible': int((visible & (iv <= 0)).sum()),
        'negative_flux_visible': int((visible & (f < 0)).sum()),
        'wave_min_A': float(w.min()), 'wave_max_A': float(w.max()),
        'mask_counts': mask_counts, 'hdu0': h0, 'hdu2': h2,
        'zwarning_set_bits': [bit for bit in range(32) if int(h2['ZWARNING']) & (1 << bit)],
        'zwarning_4_meaning': 'Bit 2 SMALL_DELTA_CHI2, not bit 4 MANY_OUTLIERS; automatic QSO/z fit is not adopted as a physical classification.',
        'noise_limits': 'HDU1 inverse variance supplies marginal pixel errors. No pixel covariance or calibration uncertainty is available; propagated colour errors are conditional on independent pixels.',
        'mask_interpretation': 'AND flags occur in every contributing exposure; OR flags in at least one. Counts overlap. Positive IVAR plus the existing narrow sky masks is the baseline; exclusion of additional flags is a declared sensitivity test.'}
    states = {}
    decisions = {}
    for key, row_index in [('mwdd_13', 13), ('mwdd_14', 14)]:
        states[(key, 'raw')] = arrays[key]
        calibrated, cal, decision = calibration(arrays[key], frozen[row_index])
        decisions[key] = decision
        states[(key, 'existing_gri_policy')] = calibrated
        if key == 'mwdd_13':
            assert cal is not None, 'Previously accepted gri anchor no longer accepted'
            shared_cal = cal
        psc, pscal, psdec = calibration(arrays[key], frozen[row_index], only_system='panstarrs')
        decisions[key+'_PS1_only_sensitivity'] = psdec
        states[(key, 'PS1_gri_sensitivity')] = psc
    states[(REF, 'raw')] = arrays[REF]
    states[(REF, 'same_existing_SDSS_gri_as_MWDD')] = transformed(arrays[REF], shared_cal)
    for label, keep in [('exclude_AND_flagged', amask == 0), ('exclude_OR_flagged', omask == 0)]:
        masked = (w[keep], f[keep], iv[keep])
        states[(REF, label)] = transformed(masked, shared_cal)
    metrics, curves = [], {}
    _, fixed_native_normalizer = binned(states[(REF, 'same_existing_SDSS_gri_as_MWDD')])
    for (key, state), arr in states.items():
        row = {'source': key, 'state': state, **measure(arr)}
        curve, normalizer = binned(arr, normalizer=fixed_native_normalizer if state.startswith('exclude_') else None)
        row['display_median_flam_5200_5500_A'] = normalizer
        metrics.append(row); curves[key+'::'+state] = curve
    def met(key, state): return next(m for m in metrics if m['source'] == key and m['state'] == state)
    def distance(a, b): return float(np.hypot(a['u1960']-b['u1960'], a['v1960']-b['v1960']))
    comparisons = []
    for state in ['raw', 'existing_gri_policy', 'PS1_gri_sensitivity']:
        left, right = met('mwdd_13', state), met('mwdd_14', state)
        comparisons.append({'comparison': 'different_instruments_SDSS_DESI', 'state': state,
            'delta_uv': distance(left, right), 'SDSS_duv': left['duv'], 'DESI_duv': right['duv'],
            'SDSS_green': left['green_dominant'], 'DESI_green': right['green_dominant'],
            'SDSS_coverage_gate': left['pipeline_coverage_gate'], 'DESI_coverage_gate': right['pipeline_coverage_gate']})
    for left_state, right_state in [('raw', 'raw'), ('existing_gri_policy', 'same_existing_SDSS_gri_as_MWDD')]:
        comparisons.append({'comparison': 'same_observation_two_representations', 'state': left_state,
            'delta_uv': distance(met('mwdd_13', left_state), met(REF, right_state))})
    native_baseline = met(REF, 'same_existing_SDSS_gri_as_MWDD')
    for state in ['exclude_AND_flagged', 'exclude_OR_flagged']:
        m = met(REF, state)
        comparisons.append({'comparison': 'native_mask_sensitivity', 'state': state,
            'delta_uv': distance(native_baseline, m), 'duv': m['duv'],
            'coverage_gate': m['pipeline_coverage_gate'], 'largest_visible_gap_A': m['largest_visible_gap_A']})
    gaia = pd.read_csv(root / manifest['gaia_input_path'], dtype={'source_id': str}).set_index('source_id').loc[SOURCE_ID]
    coord = SkyCoord(ra=gaia.ra*u.deg, dec=gaia.dec*u.deg,
        pm_ra_cosdec=gaia.pmra*u.mas/u.yr, pm_dec=gaia.pmdec*u.mas/u.yr,
        obstime=Time(gaia.ref_epoch, format='jyear'))
    epoch = Time(float(h0['MJD']), format='mjd')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', ErfaWarning)
        moved = coord.apply_space_motion(new_obstime=epoch)
    plug = SkyCoord(h0['PLUG_RA']*u.deg, h0['PLUG_DEC']*u.deg)
    dx0, dy0 = plug.spherical_offsets_to(SkyCoord(coord.ra, coord.dec))
    dx1, dy1 = plug.spherical_offsets_to(SkyCoord(moved.ra, moved.dec))
    astrometry = {'Gaia_DR3_source_id': SOURCE_ID, 'gaia_ra_ref_deg': gaia.ra, 'gaia_dec_ref_deg': gaia.dec,
        'ref_epoch_jyear': gaia.ref_epoch, 'pmra_mas_yr': gaia.pmra, 'pmdec_mas_yr': gaia.pmdec,
        'pmra_error_mas_yr': gaia.pmra_error, 'pmdec_error_mas_yr': gaia.pmdec_error,
        'parallax_mas': gaia.parallax, 'ruwe': gaia.ruwe,
        'sdss_observation_mjd': h0['MJD'], 'sdss_date_utc': epoch.isot,
        'plug_ra_deg': h0['PLUG_RA'], 'plug_dec_deg': h0['PLUG_DEC'],
        'predicted_ra_at_observation_deg': moved.ra.deg, 'predicted_dec_at_observation_deg': moved.dec.deg,
        'separation_fixed_reference_epoch_arcsec': coord.separation(plug).arcsec,
        'separation_proper_motion_propagated_arcsec': moved.separation(plug).arcsec,
        'gaia_reference_offset_from_plug_arcsec': [dx0.arcsec, dy0.arcsec],
        'gaia_observation_offset_from_plug_arcsec': [dx1.arcsec, dy1.arcsec],
        'BOSS_nominal_fibre_radius_arcsec': 1.0,
        'position_error_from_pm_only_arcsec': float(abs(epoch.jyear-gaia.ref_epoch)*np.hypot(gaia.pmra_error, gaia.pmdec_error)/1000),
        'interpretation': 'Association remains a separate review: the propagated position is 1.14 arcsec from nominal PLUG coordinates, slightly beyond the 1 arcsec geometric fibre radius. This is a centering/calibration caution, not proof of a wrong object or zero collected light. Seeing and acquisition offsets can transmit off-centre flux.',
        'limits': 'Linear tangential proper motion using the retained Gaia DR3 row. No radial velocity, perspective term, annual apparent parallax, full covariance, observing-time PSF, acquisition/ADR model or posterior association probability. MJD denotes a night, not an exact exposure midpoint.'}
    result = {'source_id': SOURCE_ID, 'identity': identity, 'native_quality': quality,
        'astrometry': astrometry, 'colour_metrics': metrics, 'comparisons': comparisons,
        'calibration_decisions': decisions, 'DESI_unit_evidence': desi_units,
        'adjudication': {'unit_layer': 'F_lambda verified by strict native-pixel identity',
            'association_layer': 'same spectral observation proven; Gaia-to-fibre centering requires review',
            'colour_layer': 'both independent instrument exports remain displaced to positive Duv after the existing gri policy; neither is green dominant',
            'current_view_proposal': 'Eligible for a versioned unit-verified overlay, with low S/N, fibre offset and calibration sensitivity prominently retained. No silent edit to the withdrawn historical corroboration.',
            'scientific_claim': 'Qualitative second-instrument colour support with quality cautions; not a precise independent colour confirmation or a new physical classification.'},
        'cautions': ['MWDD SDSS and the new direct SDSS FITS are one observation, not two independent instruments or visits.',
            'Both instrument spectra are anchored to the same retained photometry in calibrated comparisons. Agreement after that constraint is not statistically independent spectrophotometric validation.',
            'No broad flux feature or automatic SDSS redshift/classification is assigned an astrophysical cause here.',
            'The baseline integration interpolates across masked support; the CMF area statistic is not a count of measured wavelength support.',
            'Additional AND/OR mask exclusions are sensitivity tests, not automatic replacements. Large gaps make an interpolated colour less secure.'],
        'documentation': DOCS, 'input_manifest_sha256': sha((folder / 'input_manifest.json').read_bytes()),
        'old_results_modified': False}
    return jsonable(result), curves


def plot(result, curves, destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), layout='constrained')
    labels = [('mwdd_13', 'SDSS export: same observation as new FITS', '#2459a9'),
              ('mwdd_14', 'DESI export', '#cb5423')]
    for ax, state, title in zip(axes.flat[:3], ['raw', 'existing_gri_policy', 'PS1_gri_sensitivity'],
            ['A  Verified F_lambda, before photometric adjustment', 'B  Existing gri policy (SDSS anchors)', 'C  PS1 gri sensitivity (same shared photometry)']):
        for key, label, color in labels:
            curve = curves[key+'::'+state]
            ax.plot(curve[:, 0], curve[:, 1], color=color, lw=1.15, label=label)
            if key == 'mwdd_14':
                ax.fill_between(curve[:,0], curve[:,1]-curve[:,2], curve[:,1]+curve[:,2], color=color, alpha=.15)
        if state in ['raw', 'existing_gri_policy']:
            direct_state = 'raw' if state == 'raw' else 'same_existing_SDSS_gri_as_MWDD'
            curve = curves[REF+'::'+direct_state]
            ax.fill_between(curve[:,0], curve[:,1]-curve[:,2], curve[:,1]+curve[:,2], color='#2459a9', alpha=.15)
        ax.axhline(0, c='.6', lw=.5); ax.set_title(title, fontsize=10)
        ax.set(xlim=(360,830), xlabel='Vacuum wavelength (nm)', ylabel='Mean F_lambda / median at 520–550 nm')
        ax.legend(fontsize=7, loc='upper left'); ax.grid(alpha=.15)
    ax = axes[1,0]
    for state, label, color in [('same_existing_SDSS_gri_as_MWDD', 'Positive IVAR + existing sky windows', '#2459a9'),
              ('exclude_AND_flagged', 'Also exclude AND flags', '#26824b'),
              ('exclude_OR_flagged', 'Also exclude OR flags (sensitivity)', '#a2397a')]:
        curve = curves[REF+'::'+state]
        ax.plot(curve[:,0], curve[:,1], color=color, lw=1, label=label)
    ax.set(title='D  Native quality masks; same fixed correction', xlim=(360,830),
           xlabel='Vacuum wavelength (nm)', ylabel='Mean F_lambda / median at 520–550 nm')
    ax.axhline(0, c='.6', lw=.5); ax.legend(fontsize=7); ax.grid(alpha=.15)
    ax = axes[1,1]
    uv = c._BB_UV
    sel = (uv[:,0]>.18)&(uv[:,0]<.3)&(uv[:,1]>.28)&(uv[:,1]<.38)
    ax.plot(uv[sel,0], uv[sel,1], c='.45', lw=1, label='Planck continuum locus')
    for key, name, color in labels:
        for state, marker in [('raw','o'),('existing_gri_policy','s'),('PS1_gri_sensitivity','^')]:
            row = next(r for r in result['colour_metrics'] if r['source']==key and r['state']==state)
            ax.scatter(row['u1960'], row['v1960'], c=color, marker=marker, s=40,
                       label=('SDSS' if key=='mwdd_13' else 'DESI')+' / '+state.replace('_',' '))
    ax.set(title='E  Colour changes and Planck displacement', xlabel='CIE 1960 u', ylabel='CIE 1960 v',
           xlim=(.20,.24), ylim=(.325,.370)); ax.set_aspect('equal', adjustable='box')
    ax.legend(fontsize=6, loc='lower left'); ax.grid(alpha=.15)
    a = result['astrometry']; ax = axes[1,2]
    ax.add_patch(Circle((0,0),1,fill=False,color='.35',label='Nominal BOSS fibre radius 1 arcsec'))
    ax.scatter([0],[0],marker='+',c='k',s=80,label='PLUG fibre coordinate')
    p0 = a['gaia_reference_offset_from_plug_arcsec']; p1 = a['gaia_observation_offset_from_plug_arcsec']
    ax.scatter([p0[0]],[p0[1]],c='#db9131',marker='x',s=65,label='Gaia reference epoch 2016.0')
    ax.scatter([p1[0]],[p1[1]],c='#2459a9',s=45,label='Gaia propagated to SDSS night')
    ax.annotate('', xy=p1, xytext=p0, arrowprops={'arrowstyle':'->','color':'.45'})
    ax.set(title=f"F  Fibre association: offset {a['separation_proper_motion_propagated_arcsec']:.3f} arcsec",
        xlabel='East offset from PLUG (arcsec)', ylabel='North offset from PLUG (arcsec)',
        xlim=(-1.8,1.8),ylim=(-2.1,1.3)); ax.set_aspect('equal',adjustable='box')
    ax.legend(fontsize=7,loc='upper right'); ax.grid(alpha=.15)
    fig.suptitle('J1323−0129: unit resolved; precision and fibre centering remain separate questions\n'
        '20 Å display means. Shading uses native marginal errors, without covariance or calibration uncertainty.', fontsize=13)
    fig.savefig(destination,dpi=155); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--stage', action='store_true'); args=parser.parse_args()
    if args.stage: stage()
    result, curves = compute()
    (OUT/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    pd.DataFrame(result['colour_metrics']).to_csv(OUT/'colour_metrics.csv',index=False)
    pd.DataFrame(result['comparisons']).to_csv(OUT/'comparisons.csv',index=False)
    np.savez_compressed(OUT/'display_curves.npz',**curves)
    plot(result,curves,OUT/'quality_colour_association.png')
    print(json.dumps({'astrometry':result['astrometry'],'comparisons':result['comparisons'],
        'native_quality':result['native_quality'],'adjudication':result['adjudication']},indent=2))


if __name__ == '__main__': main()
