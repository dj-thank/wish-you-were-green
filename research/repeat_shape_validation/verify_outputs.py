#!/usr/bin/env python3
"""Offline replay of the repeat-shape experiment and primary-source context."""
from __future__ import annotations
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import urllib.parse
import numpy as np
from astropy.io import fits

HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);sys.modules[name]=result;spec.loader.exec_module(result)
    return result


def equivalent(expected,actual,path='result'):
    if isinstance(expected,dict):
        assert set(expected)==set(actual),(path,'different keys')
        for k in expected:equivalent(expected[k],actual[k],path+'.'+k)
    elif isinstance(expected,list):
        assert len(expected)==len(actual),(path,'different list lengths')
        for i,(x,y) in enumerate(zip(expected,actual)):equivalent(x,y,path+f'[{i}]')
    elif isinstance(expected,bool) or expected is None or isinstance(expected,str):
        assert expected==actual,(path,expected,actual)
    elif isinstance(expected,(int,float)):
        assert math.isclose(expected,actual,rel_tol=2e-8,abs_tol=2e-9),(path,expected,actual)
    else:raise TypeError((path,type(expected)))


def verify(root):
    root=Path(root).resolve();directory=root/'research/repeat_shape_validation'
    files={}
    def track(path,expected=None):
        path=Path(path)
        if not path.is_absolute():path=root/path
        found=sha(path)
        if expected is not None:assert found==expected,('SHA256 mismatch',str(path))
        files[str(path.relative_to(root))]=found
    manifest=json.loads((directory/'inputs_manifest.json').read_text())
    for name,expected in manifest['source_manifest_sha256'].items():track(name,expected)
    for p in manifest['pairs']:
        assert len(p['epochs'])==2
        assert p['epochs'][0]['exposure']!=p['epochs'][1]['exposure']
        for e in p['epochs']:track(e['path'],e['sha256'])
        if p['instrument']=='SDSS':
            anchor_rows=[]
            for epoch,photo in zip(p['epochs'],p['shared_photometry_records']):
                with fits.open(io.BytesIO(gzip.decompress((root/epoch['path']).read_bytes()))) as hdus:
                    record=hdus[2].data[0]
                    assert str(record['OBJID'])==str(photo['photometry_objid'])
                    for index,band in enumerate('gri',1):
                        assert float(record['PSFFLUX'][index])==photo[band+'_psf_flux_nanomaggies']
                        assert float(record['PSFMAGERR'][index])==photo[band+'_psf_mag_err']
                    anchor_rows.append(np.asarray(record['PSFFLUX'],float))
                    assert np.allclose(22.5-2.5*np.log10(anchor_rows[-1][1:4]),p['observed_gri'],rtol=0,atol=1e-12)
                    assert np.array_equal(np.asarray(record['PSFMAGERR'][1:4],float),p['observed_gri_errors'])
            assert np.array_equal(*anchor_rows)
    expected=json.loads((directory/'analysis_results.json').read_text())
    for name,h in expected['dependency_sha256'].items():track(name,h)
    ana=module(directory/'analyse.py','_repeat_shape_verified_analysis')
    response={f.name:hashlib.sha256(np.column_stack([f.wavelength,f.response]).astype('<f8').tobytes()).hexdigest() for f in ana.FILTERS}
    assert response==expected['filter_response_sha256']
    actual=ana.calculate(root,mc_draws=expected['settings']['pixel_noise_draws'])
    for key in ['method_version','pairs','settings','interpretation']:equivalent(expected[key],actual[key],key)
    for name,rows in ana.tables(actual).items():
        with (directory/name).open() as f:stored=list(csv.DictReader(f))
        assert len(stored)==len(rows)
        for a,b in zip(stored,rows):
            assert set(a)==set(b)
            for k,v in b.items():
                if v is None or v=='':assert a[k]==''
                elif isinstance(v,bool):assert a[k]==str(v)
                elif isinstance(v,(int,float,np.number)):assert math.isclose(float(a[k]),float(v),rel_tol=2e-8,abs_tol=2e-9),(name,k)
                else:assert a[k]==str(v),(name,k)
    # Direct Jacobian multiplication checks the compact normalization covariance
    # formula on the actual native arrays, including its cross-bin terms.
    max_covariance_error=0.
    for p in manifest['pairs']:
        w,f,v,_=ana.common_samples(p,root)
        u,_,norm,q=ana.normalize(w,f,v)
        a,_,_=ana.binner(w);dense=a.toarray();y=np.asarray(a@u.T).T
        for e in range(2):
            jac=(dense-y[e,:,None]*q[None,:])/norm[e]
            direct=(jac*v[e])@jac.T
            compact=ana.normalized_bin_covariance(a,q,f[e],v[e],norm[e],y[e])
            diff=float(np.max(np.abs(direct-compact)))
            max_covariance_error=max(max_covariance_error,diff)
            assert np.allclose(direct,compact,rtol=1e-10,atol=1e-13)
    partial=next(p for p in actual['pairs'] if p['source_id']=='3711047662972690688')
    assert list(partial['states'])==['archive']
    assert not partial['states']['archive']['colour']['available']
    assert not partial['states']['archive']['photometry']['support']['i']['available']
    assert not partial['states']['archive']['photometry']['support']['z']['available']
    assert all(not f['decompositions'] for f in partial['states']['archive']['spline_fits'])
    ctx=module(directory/'inspect_sdss_context.py','_repeat_shape_verified_context')
    computed=ctx.collect(root)
    equivalent(json.loads((directory/'sdss_context.json').read_text()),computed,'sdss_context')
    assert len(computed['coadds'])==2
    assert [r['n_physical_exposures'] for r in computed['coadds']]==[6,12]
    assert len({x for r in computed['coadds'] for x in r['contributing_mjds']})==5
    assert len(computed['exposure_headers'])==18
    assert all(r['status']=='header_recovered' for r in computed['exposure_headers'])
    assert computed['gaia_source']['source_id']=='3646912496889350784'
    assert computed['gaia_source']['phot_variable_flag']=='NOT_AVAILABLE'
    for pp in sorted((directory/'context').glob('*.provenance.json')):
        p=json.loads(pp.read_text());raw=Path(str(pp).removesuffix('.provenance.json'))
        track(raw,p['sha256']);track(pp)
        assert raw.stat().st_size==p['saved_bytes']
        assert p['retrieved_utc'] and p['started_utc']
        if raw.name.endswith('.bin'):
            assert p['http_status']==206 and p['content_range'].startswith('bytes 0-65535/')
            assert p['requested_byte_limit']==65536
        else:
            assert p['http_status']==200
            query=urllib.parse.parse_qs(urllib.parse.urlparse(p['request_url']).query)['QUERY'][0]
            assert query==ctx.GAIA_QUERY==(directory/'context/gaia_query.adql').read_text().strip()
    figures=json.loads((directory/'figures_manifest.json').read_text())
    for name,h in figures['input_sha256'].items():track(directory/name,h)
    assert len(figures['figures'])==7
    for r in figures['figures']:
        for ext in ['png','svg']:track(directory/'figures'/(r['stem']+'.'+ext),r[ext+'_sha256'])
    visual_path=directory/'visual_review.json'
    if visual_path.exists():
        visual=json.loads(visual_path.read_text());assert len(visual['figures'])==7
        assert {v['stem'] for v in visual['figures']}=={f['stem'] for f in figures['figures']}
        by_name={f['stem']:f for f in figures['figures']}
        for v in visual['figures']:
            assert v['actually_viewed'] is True and v['png_sha256']==by_name[v['stem']]['png_sha256'] and v['observation']
    else:raise AssertionError('Final seven-figure actual viewing record is required')
    for p in directory.rglob('*'):
        if p.is_file() and p.suffix in ['.py','.json','.csv','.md','.adql','.bin','.gz','.png','.svg'] and p.name!='verification.json':track(p)
    return dict(summary=dict(pairs=5,DESI_distinct_night_pairs=4,DESI_full_griz_pairs=3,DESI_partial_B_R_pairs=1,
        SDSS_disjoint_coadd_pairs=1,SDSS_contributing_nights=5,SDSS_nonoverlapping_physical_exposures=18,
        central_processing_states=sum(len(p['states']) for p in actual['pairs']),
        spline_space_fits=sum(len(s['spline_fits']) for p in actual['pairs'] for s in p['states'].values()),
        native_input_products=10,source_exposure_header_prefixes=18,exact_Gaia_target_rows=1,
        pixel_noise_perturbations_replayed=5*expected['settings']['pixel_noise_draws'],
        maximum_normalization_covariance_replay_error=max_covariance_error,
        actually_viewed_figures_with_matching_hashes=7,network_required=False,large_survey_cache_required=False,
        limits='Numerical/evidence replay, not repeat visual perception, a calibration-error distribution, intrinsic-variability confirmation, or a direct bound for J0429/J0913'),verified_file_sha256=files)


if __name__=='__main__':
    root=HERE.parents[1]
    result=verify(root)
    (HERE/'verification.json').write_text(json.dumps({'status':'PASS',**result},indent=2)+'\n')
    print(json.dumps(result['summary'],indent=2))
