#!/usr/bin/env python3
"""Extend native Gaia XP coefficient/covariance validation to all 27 nominees.

fetch: core environment, public ESA DataLink access.
reconstruct: separate pinned GaiaXPy environment, no network required.
colours: core environment, direct 3x3 XYZ covariance plus formal Gaussian draws.
"""
from __future__ import annotations
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'mpl-cache'))
import numpy as np
import pandas as pd

OUT=Path(__file__).resolve().parent/'gaia_expanded'
OUT.mkdir(exist_ok=True)
SOURCES=OUT/'sources'
SOURCES.mkdir(exist_ok=True)


def utc():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def candidates():
    t=pd.read_csv(ROOT/'research/outlier_audit/object_audit.csv',dtype={'source_id':'string'})
    return t[t.review_status.eq('multiple_instrument_colour_candidate')].source_id.tolist()


def retrieve(url,path):
    side=path.with_suffix(path.suffix+'.provenance.json')
    if path.exists() and side.exists():
        meta=json.loads(side.read_text())
        if sha(path)!=meta['sha256']:raise ValueError('Cached input changed: '+str(path))
        return path.read_bytes()
    req=urllib.request.Request(url,headers={'User-Agent':'WhiteDwarfColourResearch/0.2'})
    with urllib.request.urlopen(req,timeout=50) as response:
        data=response.read()
        meta=dict(url=url,final_url=response.url,http_status=response.status,content_type=response.headers.get('Content-Type'),
                  retrieved_utc=utc(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    path.write_bytes(data);side.write_text(json.dumps(meta,indent=2)+'\n')
    return data


def fetch_one(sid):
    try:
        url='https://gea.esac.esa.int/data-server/datalink/links?'+urllib.parse.urlencode({'ID':'Gaia DR3 '+sid})
        xml=retrieve(url,SOURCES/f'{sid}_datalink.xml')
        table=ET.fromstring(xml).find('.//{*}TABLE')
        fields=[x.attrib['name'] for x in table.findall('{*}FIELD')]
        rows=[dict(zip(fields,[(x.text or '') for x in r.findall('{*}TD')])) for r in table.findall('.//{*}TABLEDATA/{*}TR')]
        links=[r['access_url'] for r in rows if 'RETRIEVAL_TYPE=XP_CONTINUOUS' in r.get('access_url','')]
        if len(links)!=1:return dict(source_id=sid,status='XP_CONTINUOUS_not_available',datalink_rows=rows)
        url=links[0]+'&FORMAT=CSV'
        if urllib.parse.urlsplit(url).hostname!='gea.esac.esa.int':raise ValueError('Unreviewed DataLink host')
        retrieve(url,SOURCES/f'{sid}_xp_continuous.csv')
        inp=pd.read_csv(SOURCES/f'{sid}_xp_continuous.csv',dtype={'source_id':'string'})
        if len(inp)!=1 or inp.source_id.iloc[0]!=sid:raise ValueError('DataLink identity mismatch')
        return dict(source_id=sid,status='downloaded',sha256=sha(SOURCES/f'{sid}_xp_continuous.csv'))
    except Exception as exc:return dict(source_id=sid,status='failed',error=str(exc))


def fetch():
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(fetch_one,candidates()))
    (OUT/'retrieval.json').write_text(json.dumps({'created_utc':utc(),'results':results},indent=2)+'\n')
    print(pd.DataFrame(results)[['source_id','status']].to_string(index=False))


def trap(w):
    d=np.diff(w);return np.r_[d[0]/2,(d[:-1]+d[1:])/2,d[-1]/2]


def reconstruct():
    import gaiaxpy
    from gaiaxpy.core.generic_functions import array_to_symmetric_matrix
    calibrator=importlib.import_module('gaiaxpy.calibrator.calibrator')
    w=np.arange(330.,1050.5,1.)
    bases,merge=calibrator.__generate_xp_matrices_and_merge('calibrator',w,'v375wi','v142r')
    matrices={b:bases[b].get_design_matrix()*merge[b][None,:] for b in ['bp','rp']}
    grid=np.geomspace(330.,1050.,361)
    base_m,merge_m=calibrator.__generate_xp_matrices_and_merge('calibrator',grid,'v375wi','v142r')
    mwdd_matrix={b:base_m[b].get_design_matrix()*merge_m[b][None,:] for b in ['bp','rp']}
    np.savez_compressed(OUT/'calibration_design_matrices.npz',wavelength_nm=w,
        bp=matrices['bp'],rp=matrices['rp'],mwdd_wavelength_nm=grid,bp_mwdd=mwdd_matrix['bp'],rp_mwdd=mwdd_matrix['rp'])
    cmf=np.loadtxt(ROOT/'reference/CIE_xyz_1931_2deg.csv',delimiter=',')
    visible=(w>=360)&(w<=830)
    weights=np.zeros((len(w),3));weights[visible]=np.column_stack([np.interp(w[visible],cmf[:,0],cmf[:,k]) for k in [1,2,3]])*trap(w[visible])[:,None]
    results=[]
    frozen=json.load(__import__('gzip').open(ROOT/'results/screen_input_mwdd.json.gz','rt'))
    for sid in candidates():
        path=SOURCES/f'{sid}_xp_continuous.csv'
        if not path.exists():continue
        inp=pd.read_csv(path,dtype={'source_id':'string','solution_id':'string'});source=inp.iloc[0]
        bands={}
        for band in ['bp','rp']:
            coef=np.array(ast.literal_eval(source[f'{band}_coefficients']),float)
            err=np.array(ast.literal_eval(source[f'{band}_coefficient_errors']),float)
            corr=array_to_symmetric_matrix(np.array(ast.literal_eval(source[f'{band}_coefficient_correlations']),float),len(coef))
            bands[band]=(coef,corr*err[:,None]*err[None,:],int(source[f'{band}_n_relevant_bases']))
        for truncated in [False,True]:
            flux=np.zeros(len(w));variance=np.zeros(len(w));xyz=np.zeros(3);cov=np.zeros((3,3));mwdd_flux=np.zeros(len(grid))
            for band,(coef,cc,relevant) in bands.items():
                n=relevant if truncated else len(coef)
                matrix=matrices[band][:n];mxyz=matrix@weights
                flux+=coef[:n]@matrix
                variance+=np.einsum('ik,ij,jk->k',matrix,cc[:n,:n],matrix,optimize=True)
                xyz+=coef[:n]@mxyz
                cov+=mxyz.T@cc[:n,:n]@mxyz
                mwdd_flux+=coef[:n]@mwdd_matrix[band][:n]
            error=np.sqrt(np.maximum(variance,0));cov=(cov+cov.T)/2
            official,_=gaiaxpy.calibrate(path,sampling=w,truncation=truncated,save_file=False,with_correlation=False)
            official_flux=np.asarray(official.iloc[0]['flux'])
            official_error=np.asarray(official.iloc[0]['flux_error'])
            relative_flux=float(np.max(np.abs(official_flux-flux))/np.max(np.abs(flux)))
            relative_error=float(np.max(np.abs(official_error-error))/np.max(error))
            if relative_flux>1e-10 or relative_error>1e-10:raise ValueError((sid,truncated,relative_flux,relative_error))
            tag='truncated' if truncated else 'full'
            output=OUT/f'{sid}_{tag}.npz'
            np.savez_compressed(output,wavelength_nm=w,flux_w_m2_nm=flux,flux_error_w_m2_nm=error,xyz_native=xyz,xyz_covariance_native=cov)
            match=next((r for r in frozen if r.get('source_id')==sid and r.get('kind')=='Gaia_XP'),None)
            comparison={}
            if match and not truncated:
                raw=ROOT/match['raw_path']
                if raw.exists() and sha(raw)==match['sha256']:
                    old=np.loadtxt(raw,delimiter=',',skiprows=2)
                    if len(old)==len(grid):comparison={'mwdd_wavelength_max_difference_A':float(np.max(np.abs(old[:,0]-grid*10))),
                        'mwdd_full_flux_max_relative_difference':float(np.max(np.abs(old[:,1]-mwdd_flux))/np.max(np.abs(mwdd_flux))),
                        'mwdd_raw_sha256':match['sha256']}
            results.append(dict(source_id=sid,truncation=truncated,bp_bases=bands['bp'][2] if truncated else len(bands['bp'][0]),
                rp_bases=bands['rp'][2] if truncated else len(bands['rp'][0]),gaiaxpy_flux_max_relative_discrepancy=relative_flux,
                gaiaxpy_error_max_relative_discrepancy=relative_error,input_sha256=sha(path),output=output.name,output_sha256=sha(output),**comparison))
            print(sid,tag,'verified flux/error',relative_flux,relative_error,flush=True)
    metadata={'gaiaxpy_version':gaiaxpy.__version__,'created_utc':utc(),'model_versions':['v375wi','v142r'],
              'design_matrices_sha256':sha(OUT/'calibration_design_matrices.npz'),
              'propagation':'Original coefficient covariance propagated through merged BP/RP design matrices directly to XYZ; cross-band covariance unavailable and assumed zero as in GaiaXPy.',
              'results':results}
    (OUT/'reconstruction.json').write_text(json.dumps(metadata,indent=2)+'\n')


def colours():
    import colour_pipeline as c
    n_mc=200000;results=[]
    for i,sid in enumerate(candidates()):
        for tag in ['full','truncated']:
            path=OUT/f'{sid}_{tag}.npz'
            if not path.exists():continue
            data=np.load(path);xyz=data['xyz_native'];cov=data['xyz_covariance_native']
            scale=xyz[1];mean=xyz/scale;cc=cov/scale**2
            eig=np.linalg.eigvalsh(cc)
            if eig.min() < -1e-8*max(eig.max(),1e-30):raise ValueError('Indefinite XYZ covariance')
            seed=20261019+i*2+(tag=='truncated');rng=np.random.default_rng(seed)
            draws=rng.multivariate_normal(mean,cc,size=n_mc,check_valid='raise')
            physical=np.all(draws>0,axis=1);valid=draws[physical]
            den=valid[:,0]+15*valid[:,1]+3*valid[:,2]
            uv=np.column_stack([4*valid[:,0]/den,6*valid[:,1]/den])
            dist,idx=c._BB_TREE.query(uv)
            duv=dist*np.sign(uv[:,1]-c._BB_UV[idx,1])
            rgb=valid@c.XYZ_TO_RGB.T
            green=(rgb[:,1]>rgb[:,0])&(rgb[:,1]>rgb[:,2])
            central=c.xyz_to_metrics(xyz);central.update(c.planck_distance(central['u1960'],central['v1960']))
            quant=np.quantile(duv,[.025,.5,.975])
            results.append(dict(source_id=sid,reconstruction=tag,mc_seed=seed,mc_draws=n_mc,
                nonpositive_xyz_draws=int((~physical).sum()),**central,
                formal_duv_p025=float(quant[0]),formal_duv_median=float(quant[1]),formal_duv_p975=float(quant[2]),
                formal_distance_above_001_fraction=float(np.mean(dist>.01)),
                formal_green_largest_fraction=float(np.mean(green)),
                xyz_native=xyz.tolist(),xyz_covariance_native=cov.tolist(),
                caveat='Coefficient-noise model only. Conditional on positive XYZ draws; discarded count reported. No spectral calibration, BP/RP cross-calibration covariance, contamination, truncation-bias, or selection correction.'))
    table=pd.DataFrame([{k:v for k,v in r.items() if not isinstance(v,list)} for r in results]);table.to_csv(OUT/'formal_colour_results.csv',index=False)
    summary={'created_utc':utc(),'spectra':len(results),'source_count':table.source_id.nunique(),'results':results,
             'formal_model_is_not_discovery_probability':True,
             'truncation':'Full and recommended bases are alternative reconstructions of the same data, not independent observations.'}
    (OUT/'formal_colour_results.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(table[['source_id','reconstruction','duv','formal_duv_p025','formal_duv_p975','formal_green_largest_fraction']].to_string(index=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['fetch','reconstruct','colours'])
    globals()[p.parse_args().action]()
