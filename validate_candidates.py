"""Candidate-level photometry, noise, and calibration sensitivity analysis.

Monte Carlo refits a small spectral tilt using a first-order band-magnitude
Jacobian, then integrates perturbed spectra nonlinearly. Source noise is used
only where supplied. Gaia XP export has no covariance, so its simulations are
explicitly photometry-only, never a complete uncertainty budget.
"""
from pathlib import Path
from project_io import load_json
import json, os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
import colour_pipeline as c
ROOT=Path(__file__).resolve().parent
SEED=20261018

def num(value):
    try:return float(value)
    except (ValueError,TypeError):return np.nan

def anchors(rec):
    p=rec.get('photometry',{})
    result=[]
    for system,prefix,eprefix in [('sdss','s','Ds'),('panstarrs','PS_','DPS_')]:
        mags=np.array([num(p.get(prefix+b)) for b in 'gri'])
        errs=np.array([num(p.get(eprefix+b)) for b in 'gri'])
        if np.all(np.isfinite(mags)) and np.all(np.isfinite(errs)) and max(errs)<.1:
            result.append((system,mags,errs,'MWDD catalogue'))
    if rec['source_id']=='818833831355548928':
        data=json.loads((ROOT/'sdss/j0913_quality/sdss_neighbours.json').read_text())[0]['Rows'][0]
        flux=np.array([data['psfFlux_'+b] for b in 'gri'])
        iv=np.array([data['psfFluxIvar_'+b] for b in 'gri'])
        mags=22.5-2.5*np.log10(flux)
        errs=2.5/np.log(10)/flux/np.sqrt(iv)
        result=[r for r in result if r[0]!='sdss']
        result.insert(0,('sdss',mags,errs,'SDSS DR17 direct PSF flux; clean=1, deblended child'))
    return result

def get_arrays(rec):
    data=np.load(c.data_path(rec['parsed_path']));w=data['wavelength_angstrom']
    f=data['flux_original'] if 'flux_original' in data else data['flux_flam']
    iv=None
    if 'sigma' in data:
        s=data['sigma'];iv=np.divide(1,s**2,out=np.zeros_like(s),where=np.isfinite(s)&(s>0))
    elif 'ivar' in data:iv=data['ivar']
    from flux_conventions import as_flux_lambda
    f,iv,_=as_flux_lambda(w,f,iv,rec)
    return w,f,iv

def geometry(w):
    """XYZ integration coefficients on the cleaned native wavelength grid."""
    visible=(w>=3600)&(w<=8300)
    ww=w[visible]/10
    cmf=np.column_stack([np.interp(ww,c.CMF_W,c.CMF_V[:,i],left=0,right=0) for i in range(3)])
    coeff=np.zeros((len(w),3));coeff[visible]=cmf*c.trapezoid_weights(ww)[:,None]
    return coeff

def mc(w,fc,ivc,system,err,n=6000,mask_sky=True):
    # Use the same finite-pixel and narrow-sky treatment as the nominal result.
    w,fc,ivc=c.clean_spectrum(w,fc,ivc,mask_sky=mask_sky)
    scale=np.median(fc[(w>5000)&(w<7500)])
    fc=fc/scale
    sigma=np.zeros_like(fc) if ivc is None else 1/np.sqrt(ivc)/scale
    xyzcoef=geometry(w)
    # Relative synthetic-band derivatives, with official passband responses.
    bandcoef=[]
    for flt in (c.SDSS_FILTERS if system=='sdss' else c.PS1_FILTERS):
        response=np.interp(w,flt.wavelength,flt.response,left=0,right=0)
        coeff=c.trapezoid_weights(w)*w*response
        bandcoef.append(coeff)
    bandcoef=np.array(bandcoef).T
    bandflux=fc@bandcoef
    axis=(w-6200)/1000
    h=1e-4
    derivative=(c.synthetic_gri(w,fc*10**(-.4*h*axis),system)-c.synthetic_gri(w,fc*10**(+.4*h*axis),system))/(2*h)
    design=np.column_stack([np.ones(3),derivative])
    weight=1/np.maximum(err,.02)**2
    response=np.linalg.inv(design.T@(weight[:,None]*design))@design.T@np.diag(weight)
    rng=np.random.default_rng(SEED)
    rows=[]
    for start in range(0,n,250):
        k=min(250,n-start)
        noise=rng.normal(size=(k,len(w)))*sigma
        photo=rng.normal(size=(k,3))*np.maximum(err,.02)
        dmag=-(2.5/np.log(10))*(noise@bandcoef)/bandflux
        delta=(photo-dmag)@response.T
        noisy=(fc+noise)*10**(-.4*delta[:,1,None]*axis)
        xyz=noisy@xyzcoef
        xy=xyz[:,:2]/xyz.sum(axis=1)[:,None]
        den=-2*xy[:,0]+12*xy[:,1]+3
        uv=np.column_stack([4*xy[:,0]/den,6*xy[:,1]/den])
        dist,ix=c._BB_TREE.query(uv)
        duv=dist*np.sign(uv[:,1]-c._BB_UV[ix,1])
        rgb=xyz@c.XYZ_TO_RGB.T;rgb/=rgb.max(axis=1)[:,None]
        margin=rgb[:,1]-np.maximum(rgb[:,0],rgb[:,2])
        rows.append(np.column_stack([xy,uv,duv,margin,delta[:,1]]))
    values=np.vstack(rows)
    out={'mc_draws':n,'mc_seed':SEED,'mc_spectral_noise_included':ivc is not None,
         'mc_spectral_covariance':'independent resampled pixels; unmodelled correlations remain' if ivc is not None else 'not provided in MWDD XP export; photometry only',
         'mc_green_fraction_conditional':float(np.mean(values[:,5]>0)),
         'mc_outside_paper_threshold_fraction_conditional':float(np.mean(abs(values[:,4])>.01))}
    for j,name in enumerate(['x','y','u1960','v1960','duv','green_margin','cal_tilt_delta']):
        q=np.quantile(values[:,j],[.025,.16,.5,.84,.975])
        out.update({f'{name}_mc_{lab}':float(v) for lab,v in zip(['p025','p16','median','p84','p975'],q)})
    return out,values

def validate(ids, outdir=None):
    manifest=load_json(ROOT/'mwdd/manifest_enriched.json')
    recs=[r for r in manifest if r.get('source_id') in ids and r.get('parsed_path') and r['kind'] in ['DESI','Gaia_XP','SDSS']]
    rows=[];stress=[];saved=[]
    outdir=Path(outdir) if outdir is not None else ROOT/'results/validated_screen/candidates'
    outdir.mkdir(parents=True,exist_ok=True)
    for rec in recs:
        label=ids[rec['source_id']]
        common={'candidate':label,'source_id':rec['source_id'],'wdid':rec['wdid'],'kind':rec['kind'],
                'source_url':rec['source_url'],'raw_sha256':rec['sha256'],'parsed_path':rec['parsed_path']}
        try:
            w,f,iv=get_arrays(rec)
        except ValueError as exc:
            rows.append({**common,'status':'input_not_validated','error':str(exc)})
            print('INPUT NOT VALIDATED',label,rec['kind'],str(exc),flush=True)
            continue
        if w.min()>3800 or w.max()<8000:continue
        raw=c.integrate_colour(w,f,iv,mask_sky=rec['kind']!='Gaia_XP')
        rows.append({**common,'cal_system':'none','photometry_source':'none',**raw})
        for system,obs,err,phot_src in anchors(rec):
            try:
                fc,cal=c.recalibrate_gri(w,f,obs,err,system)
                if cal['cal_max_residual_mag']>.15 or abs(cal['cal_tilt_mag_per_1000A'])>.25:continue
                corr=10**(-.4*(cal['cal_offset_mag']+cal['cal_tilt_mag_per_1000A']*(w-6200)/1000))
                ivc=None if iv is None else iv/corr**2
                m=c.integrate_colour(w,fc,ivc,mask_sky=rec['kind']!='Gaia_XP')
                simulations,values=mc(w,fc,ivc,system,err,mask_sky=rec['kind']!='Gaia_XP')
                row={**common,**m,**cal,**simulations,'photometry_source':phot_src}
                for b,o,e in zip('gri',obs,err):row[f'anchor_{b}_mag']=o;row[f'anchor_{b}_error']=e
                rows.append(row)
                slug=f'{label}_{rec["kind"]}_{system}'
                np.savez_compressed(outdir/(slug+'.npz'),wavelength_angstrom=w,flux_calibrated=fc,
                                    inverse_variance=np.zeros_like(w) if ivc is None else ivc,
                                    mc_xy_uv_duv_margin_delta_b=values)
                saved.append({'label':slug,'path':str(outdir/(slug+'.npz')),**common})
                variants=[('no_sky_mask',fc,False),('nominal',fc,rec['kind']!='Gaia_XP')]
                for b in [-.1,-.05,.05,.1]:variants.append((f'additional_tilt_{b:+.2f}_mag_per_1000A',fc*10**(-.4*b*(w-6200)/1000),rec['kind']!='Gaia_XP'))
                for curvature in [-.05,.05]:
                    shape=((w-5800)/2200)**2
                    variants.append((f'5percent_curvature_{curvature:+.2f}',fc*(1+curvature*shape),rec['kind']!='Gaia_XP'))
                for variant,fv,mask in variants:
                    mm=c.integrate_colour(w,fv,ivc,mask_sky=mask)
                    stress.append({**common,'cal_system':system,'variant':variant,**mm})
                print(label,rec['kind'],system,m['hex'],'Duv',round(m['duv'],5),'95%',
                      round(simulations['duv_mc_p025'],5),round(simulations['duv_mc_p975'],5),
                      'Pgreen conditional',simulations['mc_green_fraction_conditional'],flush=True)
            except Exception as e:print('VALIDATION ERROR',label,rec['kind'],system,str(e),flush=True)
    pd.DataFrame(rows).to_csv(outdir/'validated_colours.csv',index=False)
    pd.DataFrame(stress).to_csv(outdir/'calibration_sensitivity.csv',index=False)
    (outdir/'derivative_manifest.json').write_text(json.dumps(saved,indent=2))
    return pd.DataFrame(rows)

if __name__=='__main__':
    validate({'818833831355548928':'J0913+4434','3638333660492606976':'J1323-0129',
              '3711047662972690688':'J1329+0033','1496016553207149952':'J1401+3903',
              '3204436719718449280':'J0429-0354','3690311908759604608':'J1258+0106',
              '1679189040001914880':'J1255+6712','1542337839923130624':'J1225+4706'})
