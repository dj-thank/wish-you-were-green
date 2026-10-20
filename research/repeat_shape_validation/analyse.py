#!/usr/bin/env python3
"""Descriptive repeated-observation shape projections, with explicit support.

No network access. This is not a calibration-error likelihood, a variability
test, or a replacement for the repository's frozen colour measurements.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('MPLCONFIGDIR','/tmp/wish-green-repeat-matplotlib')
import numpy as np
from astropy.io import fits
from scipy.interpolate import BSpline, PPoly
from scipy.linalg import null_space
from scipy.sparse import csr_matrix
from speclite import filters

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
import colour_pipeline as colour

SKY=((5577.34,8),(5890,6),(5896,6),(6300.30,8),(6363.78,8))
FILTERS=filters.load_filters(*['panstarrs-'+b for b in 'griz'])
STATES=('archive','common_first_gri_correction','separate_fits_shared_gri_anchors')
JOINS=((5780.,7570.),(5765.,7530.),(5795.,7610.))
BIN_WIDTH=100.
NORM=(6500.,7100.)
DOMAIN=(3600.,9824.)
MC_DRAWS=256
MC_SEED=2026102001


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean_json(x):
    if isinstance(x,dict):return {str(k):clean_json(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean_json(v) for v in x]
    if isinstance(x,np.ndarray):return clean_json(x.tolist())
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(np.floating,float)):return float(x) if np.isfinite(x) else None
    if isinstance(x,np.bool_):return bool(x)
    return x


def load_epoch(epoch,instrument,root=ROOT):
    p=root/epoch['path']
    assert sha(p)==epoch['sha256'],p
    if instrument=='DESI':
        with np.load(p) as z:
            return {a:{k:np.array(z[a+'_'+k],dtype=float if k!='mask' else np.int64)
                       for k in ['wave_A','flux','ivar','mask']} for a in 'brz'}
    raw=gzip.decompress(p.read_bytes())
    assert hashlib.sha256(raw).hexdigest()==epoch['uncompressed_sha256']
    with fits.open(io.BytesIO(raw)) as h:
        d=h[1].data
        for key in ['PLATEID','MJD','FIBERID','PLUG_RA','PLUG_DEC','BUNIT']:
            assert h[0].header[key]==epoch['metadata'][key]
        return {'s':dict(wave_A=10.**d['loglam'].astype(float),flux=d['flux'].astype(float),
             ivar=d['ivar'].astype(float),mask=d['and_mask'].astype(np.int64))}


def common_samples(pair,root=ROOT,join=JOINS[0],sdss_mask=True):
    data=[load_epoch(e,pair['instrument'],root) for e in pair['epochs']]
    waves=[];fs=[[],[]];variances=[[],[]];counts=[]
    if pair['instrument']=='DESI':
        arms=[('b',DOMAIN[0],join[0]),('r',join[0],join[1]),('z',join[1],DOMAIN[1]+.01)]
    else:arms=[('s',DOMAIN[0],DOMAIN[1]+.01)]
    for arm,low,high in arms:
        a,b=data[0][arm],data[1][arm]
        wa,wb=np.round(a['wave_A'],6),np.round(b['wave_A'],6)
        w,ia,ib=np.intersect1d(wa,wb,return_indices=True)
        assert len(w)>100
        assert np.max(np.abs(a['wave_A'][ia]-b['wave_A'][ib]))<.00002
        keep=(w>=low)&(w<high)
        for d,idx in [(a,ia),(b,ib)]:
            keep &= np.isfinite(d['flux'][idx])&np.isfinite(d['ivar'][idx])&(d['ivar'][idx]>0)
            if pair['instrument']=='DESI' or sdss_mask:keep &= d['mask'][idx]==0
        before_sky=int(keep.sum())
        for center,halfwidth in SKY:keep &= np.abs(w-center)>halfwidth
        counts.append(dict(arm=arm,aligned_pixels=len(w),common_before_sky=before_sky,retained=int(keep.sum()),
                           zero_valid_epoch=[int(np.count_nonzero((d['ivar']>0)&(d['mask']==0)))==0 for d in [a,b]]))
        waves.append(w[keep])
        for e,(d,idx) in enumerate([(a,ia),(b,ib)]):
            fs[e].append(d['flux'][idx][keep]);variances[e].append(1./d['ivar'][idx][keep])
    w=np.concatenate(waves);f=np.array([np.concatenate(x) for x in fs]);v=np.array([np.concatenate(x) for x in variances])
    ix=np.argsort(w);w,f,v=w[ix],f[:,ix],v[:,ix]
    assert np.min(np.diff(w))>0 and f.shape==v.shape==(2,len(w))
    norm=(w>=NORM[0])&(w<NORM[1]);assert norm.sum()>100
    return w,f,v,dict(arm_counts=counts,n_common_pixels=len(w),wavelength_min_A=w[0],wavelength_max_A=w[-1],
       maximum_common_gap_A=np.max(np.diff(w)),normalization_pixels=int(norm.sum()),
       negative_samples_by_epoch=(f<0).sum(axis=1).tolist(),camera_joins_A=list(join) if pair['instrument']=='DESI' else None,
       mask_rule='Both MASK==0, finite flux, IVAR>0' if pair['instrument']=='DESI' else ('Both AND_MASK==0, finite flux, IVAR>0' if sdss_mask else 'Both finite flux, IVAR>0; AND_MASK retained but not excluded'))


def normalize(w,f,v):
    q=((w>=NORM[0])&(w<NORM[1])).astype(float);q/=q.sum()
    n=f@q
    assert np.all(n>0)
    return f/n[:,None],v/n[:,None]**2,n,q


def state_data(pair,w,f,v):
    states={'archive':(f,v)};metadata={}
    if not pair['calibration_system']:
        return states,dict(unavailable_reason='No common full i band: all external-gri-correction states withheld')
    corrected=[];factors=[];fits_meta=[]
    for fe in f:
        try:
            ff,fit=colour.recalibrate_gri(w,fe*1e-17,pair['observed_gri'],pair['observed_gri_errors'],pair['calibration_system'])
            accepted=fit['cal_max_residual_mag']<.15 and abs(fit['cal_tilt_mag_per_1000A'])<.25
            fac=10.**(-.4*(fit['cal_offset_mag']+fit['cal_tilt_mag_per_1000A']*(w-6200)/1000))
            assert np.allclose(ff/1e-17,fe*fac,rtol=2e-13,atol=1e-13)
            fit['accepted']=bool(accepted);fits_meta.append(fit);factors.append(fac);corrected.append(ff/1e-17)
        except ValueError as exc:
            fits_meta.append({'accepted':False,'reason':str(exc)});factors.append(None);corrected.append(None)
    metadata['calibration_fits']=fits_meta
    metadata['anchor_system']=pair['calibration_system']
    metadata['same_photometry_does_not_mean_same_correction']=True
    if fits_meta[0]['accepted']:
        states['common_first_gri_correction']=(f*factors[0],v*factors[0]**2)
    if all(x['accepted'] for x in fits_meta):
        factors=np.array(factors);states['separate_fits_shared_gri_anchors']=(f*factors,v*factors**2)
    return states,metadata


def passband_support(w,flt):
    if w[0]>flt.wavelength[0] or w[-1]<flt.wavelength[-1]:return False,'Incomplete response support',None
    select=(w>=flt.wavelength[0])&(w<=flt.wavelength[-1])
    gap=float(np.max(np.diff(w[select])))
    return gap<=50.,None if gap<=50. else 'Interior common gap exceeds 50 A',gap


def photometry(w,u):
    mags={};support={}
    for band,flt in zip('griz',FILTERS):
        ok,reason,gap=passband_support(w,flt)
        support[band]=dict(available=ok,reason=reason,maximum_interior_gap_A=gap)
        if ok:
            flux=np.asarray(flt.get_ab_maggies(u*1e-17,w,axis=-1),float)
            if np.all(flux>0):mags[band]=(-2.5*np.log10(flux)).tolist()
            else:support[band].update(available=False,reason='Non-positive synthetic band flux')
    delta={b:float(m[1]-m[0]) for b,m in mags.items()}
    colours={a+'-'+b:delta[a]-delta[b] for a,b in [('g','r'),('r','i'),('i','z')] if a in delta and b in delta}
    return dict(normalized_magnitudes=mags,second_minus_first_mag=delta,colour_differences_mag=colours,support=support)


def colour_pair(w,u):
    if w[0]>3850 or w[-1]<8300:return dict(available=False,reason='Common spectrum does not span 3600--8300 A: no full-colour claim')
    ms=[colour.integrate_colour(w,x,mask_sky=False) for x in u]
    return dict(available=True,epochs=[{k:m[k] for k in ['u1960','v1960','duv','hex','green_channel_margin','green_dominant']} for m in ms],
                between_epoch_uv=float(np.hypot(ms[1]['u1960']-ms[0]['u1960'],ms[1]['v1960']-ms[0]['v1960'])))


def binner(w):
    edge=np.r_[np.arange(DOMAIN[0],w[-1],BIN_WIDTH),w[-1]+1e-5]
    inds=np.searchsorted(edge,w,side='right')-1
    counts=np.bincount(inds,minlength=len(edge)-1)
    good=np.flatnonzero(counts>=10)
    remap=np.full(len(counts),-1,int);remap[good]=np.arange(len(good))
    rows=remap[inds];take=rows>=0
    a=csr_matrix((1./counts[inds[take]],(rows[take],np.flatnonzero(take))),shape=(len(good),len(w)))
    return a,np.array(a@w).ravel(),counts[good]


def basis(w,spacing):
    knots=np.r_[np.repeat(w[0],4),np.arange(w[0]+spacing,w[-1],spacing),np.repeat(w[-1],4)]
    return BSpline.design_matrix(w,knots,3).toarray(),knots


def gram(knots,low=None,high=None):
    low=knots[0] if low is None else max(low,knots[0]);high=knots[-1] if high is None else min(high,knots[-1])
    edges=np.unique(np.r_[low,knots[(knots>low)&(knots<high)],high])
    x,g=np.polynomial.legendre.leggauss(5)
    xx=np.concatenate([(b+a)/2+(b-a)/2*x for a,b in zip(edges[:-1],edges[1:])])
    gg=np.concatenate([(b-a)/2*g for a,b in zip(edges[:-1],edges[1:])])/(high-low)
    bb=BSpline.design_matrix(xx,knots,3).toarray()
    return bb.T@(gg[:,None]*bb)


def supremum(knots,coef,low=None,high=None):
    low=knots[0] if low is None else max(low,knots[0]);high=knots[-1] if high is None else min(high,knots[-1])
    s=BSpline(knots,coef,3)
    rr=PPoly.from_spline(s).derivative().roots(extrapolate=False)
    xx=np.unique(np.r_[low,high,knots[(knots>low)&(knots<high)],rr[np.isfinite(rr)&(rr>=low)&(rr<=high)]])
    vals=s(xx);ix=np.argmax(np.abs(vals))
    return dict(max_abs_fraction=float(abs(vals[ix])),wavelength_of_max_abs_A=float(xx[ix]),minimum_multiplier=float(1+vals.min()),maximum_multiplier=float(1+vals.max()))


def normalized_bin_covariance(a,q,f,v,n,y):
    avq=np.asarray(a@(v*q)).ravel()
    binv=np.asarray(a.power(2)@v).ravel()
    c=(np.diag(binv)-np.outer(avq,y)-np.outer(y,avq)+np.outer(y,y)*float((q*q)@v))/n**2
    return (c+c.T)/2


def solve_projection(x,d,whitener,normrow):
    z=null_space(normrow[None,:],rcond=1e-12)
    xx=whitener@x@z;yy=whitener@d
    a,_,rank,singular=np.linalg.lstsq(xx,yy,rcond=1e-12)
    assert rank==z.shape[1]
    return z@a,float(singular[0]/singular[-1])


def photo_decomposition(w,u0,bb,knots,coef,normrow,bandnames):
    ff=[FILTERS['griz'.index(b)] for b in bandnames]
    baseline=np.array([flt.get_ab_maggies(u0,w) for flt in ff])
    h=np.array([flt.get_ab_maggies((u0[:,None]*bb).T,w,axis=-1) for flt in ff])/baseline[:,None]
    g=gram(knots);g_inv=np.linalg.inv(g)
    q=np.vstack([h,normrow]);target=np.r_[h@coef,0.]
    visible=g_inv@q.T@np.linalg.pinv(q@g_inv@q.T,rcond=1e-12)@target
    invisible=coef-visible
    assert np.max(np.abs(q@invisible))<1e-9
    fnull=u0*(1+bb@invisible)
    exact=np.array([flt.get_ab_maggies(fnull,w) for flt in ff])/baseline-1
    assert np.max(np.abs(exact))<1e-9
    full=float(coef@g@coef);v=float(visible@g@visible);n=float(invisible@g@invisible)
    assert abs(full-v-n)<1e-9*max(1,full)
    nullbounds=supremum(knots,invisible)
    colors=colour_pair(w,np.array([u0,fnull])) if nullbounds['minimum_multiplier']>0 else dict(available=False,reason='Null-component multiplier nonpositive')
    return dict(bands=bandnames,definition='Uniform-wavelength L2 orthogonal split; visible part has the same synthetic-band responses and zero reference-window mean; null part preserves these integrals exactly',
        visible_coefficients=visible.tolist(),null_coefficients=invisible.tolist(),
        full_rms_fraction=np.sqrt(full),visible_rms_fraction=np.sqrt(max(v,0)),null_rms_fraction=np.sqrt(max(n,0)),
        null_supremum=nullbounds,exact_band_fractional_change=exact.tolist(),maximum_exact_band_fractional_change=float(np.max(np.abs(exact))),
        null_colour_change=colors)


def fit_shape(w,f,v,spacing=800.,mc_draws=0,seed=MC_SEED):
    u,unv,n,q=normalize(w,f,v)
    aa,bc,count=binner(w)
    y=np.asarray(aa@u.T).T
    covs=[normalized_bin_covariance(aa,q,f[e],v[e],n[e],y[e]) for e in range(2)]
    cov=covs[0]+covs[1]
    ev,vec=np.linalg.eigh(cov);keep=ev>max(ev.max()*1e-12,1e-18)
    whitener=(vec[:,keep]/np.sqrt(ev[keep])).T
    bb,knots=basis(w,spacing)
    x=np.asarray(aa@(u[0,:,None]*bb));d=y[1]-y[0];normrow=(q*u[0])@bb
    coef,condition=solve_projection(x,d,whitener,normrow)
    fitted=x@coef;residual=d-fitted
    g=gram(knots)
    result=dict(spacing_A=spacing,knots_A=knots.tolist(),coefficients=coef.tolist(),
        n_coefficients=len(coef),covariance_rank=int(keep.sum()),n_bins=len(bc),whitened_design_condition=condition,
        terminal_knot_interval_A=float(np.diff(np.unique(knots))[-1]),short_terminal_interval=bool(np.diff(np.unique(knots))[-1]<spacing/4),
        supremum=supremum(knots,coef),interior_3900_9500_supremum=supremum(knots,coef,3900,9500),
        uniform_wavelength_rms_fraction=float(np.sqrt(coef@g@coef)),
        exact_reference_window_change=float(normrow@coef),
        binned_difference_rms_in_reference_flux_units=float(np.sqrt(np.mean(d*d))),
        binned_residual_rms_in_reference_flux_units=float(np.sqrt(np.mean(residual*residual))),
        weighted_residual_sum_squares=float(np.sum((whitener@residual)**2)),
        weighted_residual_sum_squares_is_not_a_significance_test=True,
        bin_center_A=bc.tolist(),bin_samples=count.tolist(),reference_bin_flux=y[0].tolist(),second_bin_flux=y[1].tolist(),
        bin_difference=d.tolist(),bin_difference_pixel_sigma=np.sqrt(np.maximum(np.diag(cov),0)).tolist(),fitted_bin_difference=fitted.tolist(),
        fitted_synthetic_photometry=photometry(w,np.array([u[0],u[0]*(1+bb@coef)])),
        fitted_colour=colour_pair(w,np.array([u[0],u[0]*(1+bb@coef)])) if supremum(knots,coef)['minimum_multiplier']>0 else {'available':False,'reason':'Unphysical multiplier: descriptive projection only'},
        decompositions=[])
    support=photometry(w,u)['support']
    for bands in ['gri','griz']:
        if all(support[b]['available'] for b in bands):
            result['decompositions'].append(photo_decomposition(w,u[0],bb,knots,coef,normrow,bands))
    if mc_draws:
        rng=np.random.default_rng(seed)
        draws=rng.standard_normal((2,mc_draws,len(w)))*np.sqrt(v[:,None,:])+f[:,None,:]
        nn=draws@q
        assert np.all(nn>0)
        uu=draws/nn[:,:,None]
        yy=np.asarray(aa@uu[1].T).T-np.asarray(aa@uu[0].T).T
        xx=np.stack([np.asarray(aa@(uu[0]*bb[:,j]).T).T for j in range(bb.shape[1])],axis=-1)
        norms=(uu[0]*q)@bb
        cc=np.array([solve_projection(xx[k],yy[k],whitener,norms[k])[0] for k in range(mc_draws)])
        maxima=np.array([supremum(knots,c)['max_abs_fraction'] for c in cc])
        interior=np.array([supremum(knots,c,3900,9500)['max_abs_fraction'] for c in cc])
        rms=np.sqrt(np.einsum('ij,jk,ik->i',cc,g,cc))
        band_ranges={}
        for b,flt in zip('griz',FILTERS):
            if support[b]['available']:
                fm=np.array([flt.get_ab_maggies(uue*1e-17,w,axis=-1) for uue in uu])
                ok=np.all(fm>0,axis=0)
                delta=-2.5*np.log10(fm[1,ok]/fm[0,ok])
                band_ranges[b]=dict(positive_draws=int(ok.sum()),quantiles_16_50_84_mag=np.quantile(delta,[.16,.5,.84]).tolist())
        curve=BSpline.design_matrix(bc,knots,3).toarray()@cc.T
        result['pixel_noise_perturbation']=dict(draws=mc_draws,seed=seed,conditioning='Independent Gaussian supplied pixel errors, fixed masks, fixed stage correction and central GLS weights; reference spectrum and 6500--7100 A normalizations recomputed in each draw. No coherent calibration, interpixel covariance, or photometric-anchor errors.',
            supremum_quantiles_16_50_84_fraction=np.quantile(maxima,[.16,.5,.84]).tolist(),
            interior_supremum_quantiles_16_50_84_fraction=np.quantile(interior,[.16,.5,.84]).tolist(),
            rms_quantiles_16_50_84_fraction=np.quantile(rms,[.16,.5,.84]).tolist(),
            spline_at_bin_centers_quantiles_16_50_84=np.quantile(curve,[.16,.5,.84],axis=1).tolist(),
            band_differences=band_ranges)
    return result


def calculate(root=ROOT,mc_draws=MC_DRAWS):
    manifest=json.loads((root/'research/repeat_shape_validation/inputs_manifest.json').read_text())
    results=[]
    for index,pair in enumerate(manifest['pairs']):
        w,f,v,common=common_samples(pair,root)
        states,cal=state_data(pair,w,f,v)
        r=dict(pair_id=pair['pair_id'],source_id=pair['source_id'],label=pair['label'],instrument=pair['instrument'],
            observations=[{k:e.get(k) for k in ['night','observed_mjd','exposure','fiber','targetid','contributing_mjds']} for e in pair['epochs']],
            common_samples=common,calibration=cal,states={},sensitivity=[])
        for state,(sf,sv) in states.items():
            u,_,norm,_=normalize(w,sf,sv)
            row=dict(normalization_flux=norm.tolist(),second_to_first_normalization_ratio=float(norm[1]/norm[0]),
                photometry=photometry(w,u),colour=colour_pair(w,u),spline_fits=[])
            for spacing in [400.,800.,1600.]:
                draws=mc_draws if state=='archive' and spacing==800 else 0
                row['spline_fits'].append(fit_shape(w,sf,sv,spacing,draws,MC_SEED+index))
            r['states'][state]=row
        reverse=fit_shape(w,f[::-1],v[::-1],800)
        r['reverse_archive_800']=dict(supremum=reverse['supremum'],uniform_wavelength_rms_fraction=reverse['uniform_wavelength_rms_fraction'])
        # Explicit camera-join/SDSS-mask sensitivity; no choice by favourable result.
        variants=[(f'joins_{int(a)}_{int(b)}',dict(join=(a,b))) for a,b in JOINS[1:]] if pair['instrument']=='DESI' else [('positive_ivar_only',dict(sdss_mask=False))]
        for name,kw in variants:
            sw,sf,sv,meta=common_samples(pair,root,**kw)
            uu,_,_,_=normalize(sw,sf,sv)
            fit=fit_shape(sw,sf,sv,800)
            r['sensitivity'].append(dict(name=name,common_samples=meta,photometry=photometry(sw,uu),
                 supremum=fit['supremum'],uniform_wavelength_rms_fraction=fit['uniform_wavelength_rms_fraction'],
                 terminal_knot_interval_A=fit['terminal_knot_interval_A'],short_terminal_interval=fit['short_terminal_interval'],
                 coverage_differs_from_central=bool(sw[0]!=w[0] or sw[-1]!=w[-1])))
        results.append(r)
    return clean_json(dict(method_version=1,pairs=results,settings=dict(domain_A=DOMAIN,normalization_A=NORM,bin_width_A=BIN_WIDTH,
        central_joins_A=JOINS[0],spline_spacings_A=[400,800,1600],sky_windows_A=SKY,maximum_allowed_passband_gap_A=50,
        pixel_noise_draws=mc_draws,seed=MC_SEED),
        interpretation=['Archive products are already survey flux calibrated; archive means no additional catalogue-anchor correction.',
          'The fit is a descriptive first-epoch-to-second-epoch multiplicative cubic-spline projection of signed flux differences, not an instrumental calibration estimate.',
          'A full residual covariance propagates each reference-window normalization under the supplied independent-pixel-noise assumption; noisy-reference effects are explored by perturbing both spectra.',
          'The metric depends on binning, spline space, direction, normalization, wavelength support and signal-to-noise. Low first-epoch flux can leave a large multiplicative coefficient weakly constrained.',
          'The griz-null component uses a declared uniform-wavelength L2 decomposition and preserves synthetic reference integrals. It does not impose measured-photometry error boxes.',
          'DESI pairs are distinct-night exposures; the SDSS pair consists of two disjoint multi-night coadds, spanning five nights and 18 physical exposures. Neither supplies independent instrument systematics; shared photometry does not supply independent calibration information.',
          'No J0429 or J0913 repeated exposure is present here; these cases cannot furnish their calibration-error distribution, confidence bound, or colour-flip probability.']))


def write_csv(path,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)


def tables(result):
    summary=[];bands=[];decomp=[]
    for pair in result['pairs']:
        for state,row in pair['states'].items():
            fit=next(f for f in row['spline_fits'] if f['spacing_A']==800)
            summary.append(dict(pair_id=pair['pair_id'],label=pair['label'],instrument=pair['instrument'],state=state,
                epochs=' / '.join(('coadd nominal MJD '+x['night']+'; contributing MJDs '+','.join(map(str,x['contributing_mjds']))) if pair['instrument']=='SDSS' else ('NIGHT '+x['night']) for x in pair['observations']),n_common_pixels=pair['common_samples']['n_common_pixels'],
                wavelength_min_A=pair['common_samples']['wavelength_min_A'],wavelength_max_A=pair['common_samples']['wavelength_max_A'],
                spectrum_scale_ratio=row['second_to_first_normalization_ratio'],
                spline_rms_percent=100*fit['uniform_wavelength_rms_fraction'],spline_supremum_percent=100*fit['supremum']['max_abs_fraction'],
                spline_supremum_wavelength_A=fit['supremum']['wavelength_of_max_abs_A'],interior_supremum_percent=100*fit['interior_3900_9500_supremum']['max_abs_fraction'],
                full_colour_available=row['colour']['available'],between_epoch_uv=row['colour'].get('between_epoch_uv'),
                supplied_pixel_noise_rms16_percent=100*fit['pixel_noise_perturbation']['rms_quantiles_16_50_84_fraction'][0] if 'pixel_noise_perturbation' in fit else '',
                supplied_pixel_noise_rms84_percent=100*fit['pixel_noise_perturbation']['rms_quantiles_16_50_84_fraction'][2] if 'pixel_noise_perturbation' in fit else ''))
            for band,support in row['photometry']['support'].items():
                bands.append(dict(pair_id=pair['pair_id'],label=pair['label'],state=state,band=band,available=support['available'],reason=support['reason'],
                    second_minus_first_normalized_mag=row['photometry']['second_minus_first_mag'].get(band),
                    spline_predicted_difference_mag=fit['fitted_synthetic_photometry']['second_minus_first_mag'].get(band),
                    maximum_common_gap_A=support['maximum_interior_gap_A']))
            for fit in row['spline_fits']:
                for d in fit['decompositions']:
                    decomp.append(dict(pair_id=pair['pair_id'],label=pair['label'],state=state,spacing_A=fit['spacing_A'],bands=d['bands'],
                        rms_percent=100*d['full_rms_fraction'],photometry_visible_rms_percent=100*d['visible_rms_fraction'],photometry_null_rms_percent=100*d['null_rms_fraction'],
                        null_supremum_percent=100*d['null_supremum']['max_abs_fraction'],null_minimum_multiplier=d['null_supremum']['minimum_multiplier'],
                        exact_maximum_band_fractional_change=d['maximum_exact_band_fractional_change'],
                        null_colour_uv=d['null_colour_change'].get('between_epoch_uv')))
    return {'repeat_shape_summary.csv':summary,'synthetic_band_differences.csv':bands,'spline_decomposition.csv':decomp}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mc-draws',type=int,default=MC_DRAWS)
    args=parser.parse_args()
    result=calculate(mc_draws=args.mc_draws)
    for name,rows in tables(result).items():write_csv(HERE/name,rows)
    deps=[HERE/'analyse.py',HERE/'inputs_manifest.json',ROOT/'colour_pipeline.py',ROOT/'project_io.py',ROOT/'requirements-core.txt',ROOT/'reference/CIE_xyz_1931_2deg.csv']
    result['dependency_sha256']={str(p.relative_to(ROOT)):sha(p) for p in deps if p.exists()}
    result['filter_response_sha256']={flt.name:hashlib.sha256(np.column_stack([flt.wavelength,flt.response]).astype('<f8').tobytes()).hexdigest() for flt in FILTERS}
    (HERE/'analysis_results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps([{'label':p['label'],'states':list(p['states']),'archive_delta_mag':p['states']['archive']['photometry']['second_minus_first_mag'],
        'archive_800_RMS_percent':100*p['states']['archive']['spline_fits'][1]['uniform_wavelength_rms_fraction'],
        'archive_800_sup_percent':100*p['states']['archive']['spline_fits'][1]['supremum']['max_abs_fraction']} for p in result['pairs']],indent=2))


if __name__=='__main__':main()
