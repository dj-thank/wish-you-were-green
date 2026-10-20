#!/usr/bin/env python3
"""Offline reproduction of the October 20 original-data and identifiability work.

This validates numerical calculations and saved viewing provenance; it cannot
repeat human/AI visual judgement or certify an astrophysical discovery.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('MPLBACKEND','Agg')
os.environ.setdefault('MPLCONFIGDIR','/tmp/wish-green-oct20-verify')


def require(value,message):
    if not value:raise AssertionError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_visual_and_targeted(root):
    import numpy as np
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    from research.unit_resolution_followup.root_targeted import compute
    from research.unit_resolution_followup.compact_inputs import CompactInputs
    from research.repeat_shape_validation.verify_outputs import equivalent
    b=root/'research/measurement_design';checked={}
    def track(path,digest=None):
        path=Path(path)
        if not path.is_absolute():path=root/path
        path=path.resolve();require(path.is_relative_to(root),'Path outside checkout')
        actual=sha(path);require(digest is None or actual==digest,f'Hash mismatch: {path}')
        checked[str(path.relative_to(root))]=actual
        return path
    review=json.loads(track(b/'visual_review.json').read_text())
    panels=review['photometry_panels'];figures=review['summary_figures']
    cohort=json.loads(track(b/'measured_results.json').read_text())['cohort']
    require(len(panels)==25 and {r['source_id'] for r in panels}==set(cohort),'All 25 plotted targets must have a viewing entry')
    require({(r['figure'],r['panel']) for r in panels}=={(f'photometry_sheet_{i:02d}.png',j) for i in range(1,6) for j in range(1,6)},'Missing/duplicated panel')
    for r in panels+figures:
        require(r['status']=='actually_viewed' and len(r['observation'])>30,'A prepared figure is not a viewing record')
        track(b/r['figure'],r['figure_sha256'])
    require(len(figures)==4,'Summary figure census')
    with track(b/'individual_photometry_review.csv').open() as f:stored=list(csv.DictReader(f))
    require(len(stored)==25,'Individual CSV census')
    for p,r in zip(panels,stored):
        for k,v in p.items():require(str(v)==r[k],f'Viewing CSV differs: {k}')
    base=root/'research/unit_resolution_followup/root_targeted'
    expected=json.loads(track(base/'results.json').read_text())
    for p,digest in expected['input_sha256'].items():track(p,digest)
    actual,_=compute(root);equivalent(expected['rows'],actual,'targeted native diagnostics')
    track(base/expected['figure'],expected['figure_sha256'])
    v=json.loads(track(base/'visual_review.json').read_text())
    require(v['status']=='actually_viewed' and v['rows_actually_viewed']==[6462,6652,6951,7993,8040],'Targeted panels not recorded')
    track(base/v['figure'],v['figure_sha256'])
    context=json.loads(track(base/'classification_context.json').read_text())
    require(context['row_index']==6462 and context['source_id']=='767756877680612864','Wrong literature-context source')
    pub=SkyCoord('11h37m32.32s','+40d54m58.3s')
    plug=SkyCoord(context['original_PLUG_ra_deg']*u.deg,context['original_PLUG_dec_deg']*u.deg)
    np.testing.assert_allclose(pub.separation(plug).arcsec,context['published_name_to_PLUG_separation_arcsec'],rtol=0,atol=1e-10)
    store=CompactInputs(root);row=next(x for x in actual if x['row_index']==6462);native=store.load(row['reference_key'])
    header=store.entries[row['reference_key']]['raw_header']
    require([header['PLATEID'],header['MJD'],header['FIBERID']]==context['original_SDSS_plate_MJD_fibre'],'Wrong original observation')
    require(row['reference_original_sha256']==context['native_reference_original_sha256'],'Wrong original SHA')
    for wavelength in context['observed_native_peak_wavelengths_vacuum_A']:
        index=int(np.argmin(abs(native['wave']-wavelength)))
        require(abs(native['wave'][index]-wavelength)<=.006,'Reported peak is not a rounded native sample')
        require(native['ivar'][index]>0,'Claimed supported peak has invalid IVAR')
    return {'summary':{'photometry_object_panels':25,'summary_figures':4,'targeted_native_records':5,'known_binary_context_position_recalculated':True},'checked_files':checked,'limits':'Hashes verify saved actual-viewing records; replay cannot perform the original visual judgement or independently certify literature counterpart identity.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--json',type=Path)
    parser.add_argument('--write-unit-report',action='store_true',
                        help='Also save the fully replayed unit/viewer component result in the verified checkout')
    args=parser.parse_args();root=args.root.resolve()
    require((root/'colour_pipeline.py').is_file(),'Not the research checkout')
    sys.path.insert(0,str(root))
    def denied(*_args,**_kwargs):raise RuntimeError('Network access is forbidden during offline scientific reproduction')
    socket.socket.connect=denied;socket.socket.connect_ex=denied
    socket.create_connection=denied;socket.getaddrinfo=denied
    jobs=[
        ('original_units_native_support_and_individual_review','research.unit_resolution_followup.verify_outputs'),
        ('actual_additional_catalogue_photometry','research.independent_photometry.verify_outputs'),
        ('repeated_spectra_shape_and_context','research.repeat_shape_validation.verify_outputs'),
        ('whole_colour_set_measurement_design','research.measurement_design.verify_outputs'),
        ('actual_added_measurement_constraints','research.measurement_design.verify_measured'),
        ('independently_rebuilt_selected_colour_sets','research.measurement_design.independent_review.run_review'),
        ('targeted_native_features_and_published_classification_context','research.unit_resolution_followup.targeted_followup.verify_outputs')]
    groups=[];checked={}
    for name,module in jobs:
        result=importlib.import_module(module).verify(root)
        require(isinstance(result,dict) and 'summary' in result,f'Incomplete verifier result: {module}')
        if name=='original_units_native_support_and_individual_review' and args.write_unit_report:
            (root/'research/unit_resolution_followup/verification_summary.json').write_text(
                json.dumps(result,indent=2,ensure_ascii=False)+'\n')
        files=result.get('checked_files')
        if not isinstance(files,dict):
            files=result.get('verified_file_sha256',{})
        require(isinstance(files,dict) and bool(files),f'No input hashes: {module}')
        for p,digest in files.items():
            path=Path(p)
            if path.is_absolute():p=str(path.relative_to(root))
            if p in checked:require(checked[p]==digest,f'Conflicting verified hash: {p}')
            checked[p]=digest
        groups.append({'name':name,'status':'PASS','summary':result['summary']})
        print('PASS '+name+': '+json.dumps(result['summary'],ensure_ascii=False),flush=True)
    result=verify_visual_and_targeted(root)
    for p,digest in result['checked_files'].items():
        if p in checked:require(checked[p]==digest,f'Conflicting hash: {p}')
        checked[p]=digest
    groups.append({'name':'actual_viewing_provenance_and_selected_original_pixels','status':'PASS','summary':result['summary']})
    checked[str(Path(__file__).resolve().relative_to(root))]=sha(__file__)
    report={'status':'PASS','executed_utc':datetime.now(timezone.utc).isoformat(),'offline_network_blocked':True,'groups':groups,'verified_file_count':len(checked),'verified_file_sha256':dict(sorted(checked.items())),
            'scope_limits':'Numerical replay and saved source/viewing provenance. No survey download, new visual judgement, atmosphere fitting, independent catalogue calibration assumption, population discovery significance or formal interval-arithmetic proof.'}
    if args.json:
        args.json.parent.mkdir(parents=True,exist_ok=True);args.json.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(f'PASS October 20 research: {len(groups)} groups; {len(checked)} file hashes. No network.',flush=True)

if __name__=='__main__':main()
