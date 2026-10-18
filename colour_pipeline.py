"""Reproducible, conservative screening of public stellar F_lambda spectra.

No colour is a discovery claim. Observed colours, calibration-sensitive colours,
published chromaticities and plausible new candidates are recorded separately.
"""
from __future__ import annotations

import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'mpl-cache'))
from project_io import load_json
import json
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
import colour
from astropy.coordinates import SkyCoord
from astropy import units as u
from speclite import filters

CMF = colour.MSDS_CMFS['CIE 1931 2 Degree Standard Observer']
CMF_W = np.asarray(CMF.wavelengths)
CMF_V = np.asarray(CMF.values)
if (ROOT/'reference/CIE_xyz_1931_2deg.csv').exists():
    _official=np.loadtxt(ROOT/'reference/CIE_xyz_1931_2deg.csv',delimiter=',')
    CMF_W,CMF_V=_official[:,0],_official[:,1:]
XYZ_TO_RGB = np.array([[3.2410,-1.5374,-.4986],[-.9692,1.8760,.0416],[.0556,-.2040,1.0570]])
SDSS_FILTERS = filters.load_filters('sdss2010-g','sdss2010-r','sdss2010-i')
PS1_FILTERS = filters.load_filters('panstarrs-g','panstarrs-r','panstarrs-i')

def data_path(value):
    """Resolve both the original analysis manifest and relocated bundles."""
    p=Path(value)
    marker='wd-colour-research/'
    if marker in str(value):return ROOT/str(value).split(marker,1)[1]
    if p.is_absolute() and p.exists():return p
    return ROOT/p

def trapezoid_weights(w):
    d=np.diff(w); out=np.empty(len(w));out[0]=d[0]/2;out[-1]=d[-1]/2
    out[1:-1]=(d[:-1]+d[1:])/2
    return out

def blackbody(w_nm, t):
    w=np.asarray(w_nm)*1e-9
    b=w**-5 / np.expm1(np.minimum(1.438776877e-2/(w*t),700))
    return b/np.max(b)

def xyz_to_metrics(xyz):
    xyz=np.asarray(xyz,dtype=float)
    if not np.all(np.isfinite(xyz)) or np.min(xyz)<=0: raise ValueError('Non-positive XYZ')
    x,y=(xyz/xyz.sum())[:2]
    den=-2*x+12*y+3
    uu,vv=4*x/den,6*y/den
    rgb=XYZ_TO_RGB@xyz
    rgb/=rgb.max()
    in_gamut=bool(np.all(rgb>=0))
    # Clipping is display-only. Chromaticity and ranking always use unclipped XYZ.
    rgbd=np.clip(rgb,0,1)
    s=np.where(rgbd<=.0031308,12.92*rgbd,1.055*rgbd**(1/2.4)-.055)
    vals=np.rint(255*s).astype(int)
    return {'x':float(x),'y':float(y),'u1960':float(uu),'v1960':float(vv),
            'r_linear':float(rgb[0]),'g_linear':float(rgb[1]),'b_linear':float(rgb[2]),
            'r':int(vals[0]),'g':int(vals[1]),'b':int(vals[2]),
            'hex':'#'+''.join(f'{v:02X}' for v in vals),'in_srgb_gamut':in_gamut,
            'green_dominant':bool(rgb[1]>max(rgb[0],rgb[2])),
            'green_channel_margin':float(rgb[1]-max(rgb[0],rgb[2]))}

_TW=trapezoid_weights(CMF_W)
_BB_T=np.geomspace(1000,1e8,8000)
_BB_XYZ=np.array([(CMF_V*(_TW*blackbody(CMF_W,t))[:,None]).sum(axis=0) for t in _BB_T])
_RJ=(CMF_V*(_TW*CMF_W**-4)[:,None]).sum(axis=0)
_BB_XYZ=np.vstack([_BB_XYZ,_RJ]);_BB_T=np.r_[_BB_T,np.inf]
_BB_XY=_BB_XYZ[:,:2]/_BB_XYZ.sum(axis=1)[:,None]
_BB_DEN=-2*_BB_XY[:,0]+12*_BB_XY[:,1]+3
_BB_UV=np.column_stack([4*_BB_XY[:,0]/_BB_DEN,6*_BB_XY[:,1]/_BB_DEN])
_BB_TREE=cKDTree(_BB_UV)

def planck_distance(uu,vv):
    dist,ix=_BB_TREE.query([uu,vv]); bv=_BB_UV[ix]
    return {'duv':float(dist*np.sign(vv-bv[1])), 'distance_planck_uv':float(dist),
            'nearest_planck_temperature_K':float(_BB_T[ix]),
            'nearest_planck_u':float(bv[0]),'nearest_planck_v':float(bv[1]),
            'nearest_is_RJ_limit':bool(ix==len(_BB_T)-1 or _BB_T[ix]>1e7)}

def clean_spectrum(w_ang,f,ivar=None,mask_sky=True):
    w=np.asarray(w_ang,dtype=float);f=np.asarray(f,dtype=float)
    good=np.isfinite(w)&np.isfinite(f)&(w>0)
    if ivar is not None: good &= np.isfinite(ivar)&(np.asarray(ivar)>0)
    w,f=w[good],f[good]
    inv=None if ivar is None else np.asarray(ivar,dtype=float)[good]
    order=np.argsort(w);w,f=w[order],f[order]
    if inv is not None: inv=inv[order]
    unique=np.r_[True,np.diff(w)>0];w,f=w[unique],f[unique]
    if inv is not None:inv=inv[unique]
    if len(w)<30:raise ValueError('Too few valid spectral pixels')
    # Narrow airglow windows only. Do not remove broad astrophysical absorption.
    if mask_sky:
        keep=np.ones(len(w),dtype=bool)
        for centre,halfwidth in [(5577.34,8),(5890,6),(5896,6),(6300.30,8),(6363.78,8)]:
            keep &= abs(w-centre)>halfwidth
        w,f=w[keep],f[keep]
        if inv is not None:inv=inv[keep]
    return w,f,inv

def integrate_colour(w_ang,f,ivar=None,mask_sky=True):
    w,f,iv=clean_spectrum(w_ang,f,ivar,mask_sky)
    wmin,wmax=w.min(),w.max()
    # No invented blue flux. Incomplete spectra cannot enter candidate ranking.
    eligible=bool(wmin<=3850 and wmax>=7800)
    select=(w>=3600)&(w<=8300)
    w,f=w[select]/10,f[select]
    if iv is not None:iv=iv[select]
    if len(w)<30:raise ValueError('Too little visible wavelength coverage')
    cmf=np.column_stack([np.interp(w,CMF_W,CMF_V[:,i],left=0,right=0) for i in range(3)])
    coeff=cmf*trapezoid_weights(w)[:,None]
    xyz=coeff.T@f
    m=xyz_to_metrics(xyz);m.update(planck_distance(m['u1960'],m['v1960']))
    frac=np.trapezoid(cmf,w,axis=0)/np.trapezoid(CMF_V,CMF_W,axis=0)
    m.update({'wave_min_A':float(wmin),'wave_max_A':float(wmax),'coverage_eligible':eligible,
              'cmf_min_coverage':float(frac.min()),'n_visible_pixels':len(w),
              'visible_negative_fraction':float(np.mean(f<0)),
              'largest_visible_gap_A':float(np.max(np.diff(w))*10)})
    if iv is not None:
        cov=(coeff.T/iv)@coeff
        # Analytic first-order error propagation, without claiming calibration errors.
        xx,yy,zz=xyz; den=xx+15*yy+3*zz
        jac=np.array([[4*(den-xx),-60*xx,-12*xx],[-6*yy,6*(den-15*yy),-18*yy]])/den**2
        cuv=jac@cov@jac.T
        m.update({'u1960_stat_error':float(np.sqrt(max(cuv[0,0],0))),
                  'v1960_stat_error':float(np.sqrt(max(cuv[1,1],0))),
                  'uv_stat_error_max':float(np.sqrt(max(np.linalg.eigvalsh(cuv).max(),0)))})
    return m

def synthetic_gri(w,f,system='sdss'):
    # Absolute scaling is irrelevant to colours, but avoid underflow/negative bands.
    vals=[]
    for flt in (SDSS_FILTERS if system=='sdss' else PS1_FILTERS):
        if w.min()>flt.wavelength.min() or w.max()<flt.wavelength.max():
            vals.append(np.nan); continue
        vals.append(float(flt.get_ab_magnitude(f,w)))
    return np.array(vals)

def recalibrate_gri(w,f,observed,errors=None,system='sdss'):
    obs=np.asarray(observed,float);valid=np.isfinite(obs)&(obs>0)&(obs<35)
    if np.count_nonzero(valid)<3:raise ValueError('Three valid gri magnitudes required')
    err=np.asarray(errors if errors is not None else [.03]*3,float)
    if np.any(np.isfinite(err)&(err>.1)):
        raise ValueError('Photometric uncertainty exceeds 0.10 mag; no reliable gri anchor')
    # A modest error floor reflects non-simultaneity and calibration uncertainty.
    err=np.where(np.isfinite(err)&(err>0),np.maximum(err,.02),.03)
    raw=synthetic_gri(w,f,system)
    if not np.all(np.isfinite(raw)):raise ValueError('Incomplete band coverage or nonpositive band flux')
    axis=(w-6200)/1000
    def mag_at(a,b):return synthetic_gri(w,f*10**(-.4*(a+b*axis)),system)
    x0=[float(np.mean(obs-raw)),0.]
    fit=least_squares(lambda p:(mag_at(*p)-obs)/err,x0,bounds=([-100,-3],[100,3]),max_nfev=60)
    a,b=fit.x;fc=f*10**(-.4*(a+b*axis));mags=synthetic_gri(w,fc,system)
    cov=np.linalg.pinv(fit.jac.T@fit.jac)
    return fc,{'cal_system':system,'cal_offset_mag':float(a),'cal_tilt_mag_per_1000A':float(b),
               'cal_tilt_error':float(np.sqrt(cov[1,1])),
               'cal_g_residual':float(mags[0]-obs[0]),'cal_r_residual':float(mags[1]-obs[1]),
               'cal_i_residual':float(mags[2]-obs[2]),
               'cal_max_residual_mag':float(np.max(abs(mags-obs))),
               'raw_g_minus_r':float(raw[0]-raw[1]),'raw_r_minus_i':float(raw[1]-raw[2]),
               'photo_g_minus_r':float(obs[0]-obs[1]),'photo_r_minus_i':float(obs[1]-obs[2])}

def analyze_record(rec, *, legacy_unverified_units=False):
    """Screen one spectrum; choose SDSS, then PS1 if no reliable SDSS anchor.

    This is a discovery *screen*. Invalid photometry is never used to force a
    colour. Unanchored spectra remain labelled and need follow-up validation.
    MWDD SDSS exports require a raw-SHA-matched F_nu/F_lambda determination.
    The explicit legacy option reproduces the flawed 0.1 screen for auditing;
    its results must not be promoted into the corrected candidate selection.
    """
    row={k:rec.get(k) for k in ['wdid','source_id','spectype','teff','ra_deg','dec_deg','kind','source_url','star_page_url','parsed_path','raw_path','sha256','selection_group','spectrum_id','photometry_clean']}
    from flux_conventions import as_flux_lambda, resolve_flux_convention, UnverifiedFluxConvention
    row.update(resolve_flux_convention(rec))
    row['calibrated']=False
    try:
        sp=np.load(data_path(rec['parsed_path']));w=sp['wavelength_angstrom']
        f=sp['flux_original'] if 'flux_original' in sp else sp['flux_flam']
        iv=None
        if 'sigma' in sp:
            ss=sp['sigma'];iv=np.divide(1,ss**2,out=np.zeros_like(ss),where=np.isfinite(ss)&(ss>0))
        elif 'ivar' in sp: iv=sp['ivar']
        if legacy_unverified_units:
            row.update(flux_units_validated=False,flux_input_convention='legacy_assumed_flambda',
                       flux_unit_evidence='Historical reproduction only; known mixed-unit screen',
                       flux_conversion_applied=False)
        else:
            f,iv,unit_info=as_flux_lambda(w,f,iv,rec)
            row.update(unit_info)
        m=integrate_colour(w,f,iv,mask_sky=rec['kind']!='Gaia_XP')
        row.update({'raw_'+k:v for k,v in m.items()});row.update(m);row['calibrated']=False
        p=rec.get('photometry',{})
        def num(k):
            try:return float(p.get(k,np.nan))
            except (ValueError,TypeError):return np.nan
        errors=[]
        for system,prefix,eprefix in [('sdss','s','Ds'),('panstarrs','PS_','DPS_')]:
            obs=[num(prefix+b) for b in 'gri'];err=[num(eprefix+b) for b in 'gri']
            if not all(np.isfinite(obs)):continue
            try:
                fc,cal=recalibrate_gri(w,f,obs,err,system=system)
                if cal['cal_max_residual_mag']>=.15 or abs(cal['cal_tilt_mag_per_1000A'])>=.25:
                    raise ValueError('Rejected calibration: residual >=0.15 mag or |tilt| >=0.25 mag/1000 A')
                corr=10**(-.4*(cal['cal_offset_mag']+cal['cal_tilt_mag_per_1000A']*(w-6200)/1000))
                ivc=None if iv is None else iv/corr**2
                mc=integrate_colour(w,fc,ivc,mask_sky=rec['kind']!='Gaia_XP')
                row.update(mc);row.update(cal);row['calibrated']=True
                uv0=np.array([mc['u1960'],mc['v1960']]);shifts=[]
                for shift in [-max(2*cal['cal_tilt_error'],.03),max(2*cal['cal_tilt_error'],.03)]:
                    ms=integrate_colour(w,fc*10**(-.4*shift*(w-6200)/1000),ivc,mask_sky=rec['kind']!='Gaia_XP')
                    shifts.append(np.linalg.norm(np.array([ms['u1960'],ms['v1960']])-uv0))
                row['uv_tilt_stress_max']=float(max(shifts))
                break
            except Exception as e:errors.append(system+': '+str(e))
        if errors:row['calibration_notes']='; '.join(errors)
        if iv is not None:
            good=np.isfinite(iv)&(iv>0)&(w>4000)&(w<7500)
            row['visible_median_pixel_snr']=float(np.median(f[good]*np.sqrt(iv[good]))) if np.any(good) else np.nan
        row['status']='ok'
    except UnverifiedFluxConvention as e:row['status']='unit_unverified';row['error']=str(e)
    except Exception as e:row['status']='error';row['error']=str(e)
    return row

def load_exclusions():
    p=ROOT/'novelty/hollands2026_exclusions_unique.csv'
    return pd.read_csv(p) if p.exists() else None

def inspect_mwdd_manifest():
    return load_json(ROOT/'mwdd/manifest_enriched.json')

def analyze_mwdd():
    """Current unit-aware MWDD calculation; historical tables are not overwritten."""
    rows=[analyze_record(rec) for rec in inspect_mwdd_manifest() if rec.get('parsed_path')]
    out=pd.DataFrame(rows)
    destination=ROOT/'results/validated_screen'
    destination.mkdir(parents=True,exist_ok=True)
    out.to_csv(destination/'mwdd_screen.csv',index=False)
    return out


def save_reference_data():
    d=ROOT/'reference';d.mkdir(exist_ok=True)
    pd.DataFrame(np.column_stack([CMF_W,CMF_V]),columns=['wavelength_nm','xbar','ybar','zbar']).to_csv(d/'cie1931_2deg.csv',index=False)
    pd.DataFrame(np.column_stack([_BB_T,_BB_XY,_BB_UV]),columns=['temperature_K','x','y','u1960','v1960']).to_csv(d/'planckian_locus.csv',index=False)

if __name__=='__main__':
    save_reference_data()
    out=analyze_mwdd()
    cols=[c for c in ['wdid','kind','hex','duv','raw_hex','raw_duv','calibrated','cal_max_residual_mag','coverage_eligible','visible_negative_fraction'] if c in out]
    print('spectra',len(out),'objects',out.wdid.nunique())
    print(out[cols].to_string(index=False,max_rows=30))
