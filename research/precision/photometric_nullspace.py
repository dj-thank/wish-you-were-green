#!/usr/bin/env python3
"""How much smooth spectral distortion can three photometric anchors miss?

Linear programming finds a bounded multiplicative cubic-spline distortion
that changes the ordering of linear sRGB channels while preserving all three
synthetic gri photon fluxes exactly. This is an adversarial sensitivity
experiment, NOT an inferred calibration error, posterior or atmosphere model.
"""
from __future__ import annotations
import os
from pathlib import Path
import sys
import json
import hashlib

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'mpl-cache'))
import numpy as np
import pandas as pd
from scipy.interpolate import BSpline, PPoly
from scipy.optimize import linprog
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import colour_pipeline as c

OUT=Path(__file__).resolve().parent


def smooth_basis(w,spacing_A):
    interior=np.arange(w.min()+spacing_A,w.max(),spacing_A)
    knots=np.r_[np.repeat(w.min(),4),interior,np.repeat(w.max(),4)]
    return BSpline.design_matrix(w,knots,k=3).toarray(),knots


def colour_operator(w):
    select=(w>=3600)&(w<=8300)
    ww=w[select]/10
    cmf=np.column_stack([np.interp(ww,c.CMF_W,c.CMF_V[:,i],left=0,right=0) for i in range(3)])
    coeff=np.zeros((len(w),3))
    coeff[select]=cmf*c.trapezoid_weights(ww)[:,None]
    return coeff


def exact_photometry_matrix(w,f,basis,filterset):
    # speclite's actual integration/interpolation operator is used both for
    # the constraints and for a fresh numerical magnitude residual check.
    baseline=np.array([flt.get_ab_maggies(f,w) for flt in filterset])
    changes=np.array([flt.get_ab_maggies((f[:,None]*basis).T,w,axis=-1) for flt in filterset])
    return changes/baseline[:,None]


def minimum_flip(w,f,spacing_A,pair='G-R'):
    basis,knots=smooth_basis(w,spacing_A)
    filt=c.PS1_FILTERS
    anchors=exact_photometry_matrix(w,f,basis,filt)
    coeff=colour_operator(w)
    xyz=coeff.T@f
    rgb=c.XYZ_TO_RGB@xyz
    first,second={'G-R':(1,0),'G-B':(1,2)}[pair]
    colour_row=(c.XYZ_TO_RGB[first]-c.XYZ_TO_RGB[second])@coeff.T
    difference=float(colour_row@f)
    scale=float(np.max(np.abs(rgb)))
    change=(colour_row*f)@basis/scale
    k=basis.shape[1]
    aeq=np.column_stack([np.vstack([anchors,change]),np.zeros(4)])
    beq=np.r_[np.zeros(3),-difference/scale]
    # Dense grid constraints also bound between the observed pixels and in
    # the narrow masked intervals. Native points alone need not bound a spline.
    dense=np.linspace(w.min(),w.max(),int(np.ceil((w.max()-w.min())/2))+1)
    bdense=BSpline.design_matrix(dense,knots,k=3).toarray()
    bounds_basis=np.vstack([basis,bdense])
    objective=np.r_[np.zeros(k),1.]
    for iteration in range(12):
        aub=np.vstack([np.column_stack([bounds_basis,-np.ones(len(bounds_basis))]),
                       np.column_stack([-bounds_basis,-np.ones(len(bounds_basis))])])
        fit=linprog(objective,A_ub=aub,b_ub=np.zeros(2*len(bounds_basis)),A_eq=aeq,b_eq=beq,
                    bounds=[(None,None)]*k+[(0,.95)],method='highs',
                    options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9})
        if not fit.success:break
        spline=BSpline(knots,fit.x[:-1],3)
        roots=PPoly.from_spline(spline).derivative().roots(extrapolate=False)
        roots=roots[np.isfinite(roots)&(roots>=w.min())&(roots<=w.max())]
        extrema=np.unique(np.r_[roots,knots])
        exact_max=float(np.max(np.abs(spline(extrema))))
        if exact_max-fit.x[-1]<=2e-9:break
        bounds_basis=np.vstack([bounds_basis,BSpline.design_matrix(extrema,knots,k=3).toarray()])
    common=dict(spacing_A=spacing_A,colour_boundary=pair,n_spline_coefficients=k,
                success=bool(fit.success),solver_message=fit.message)
    if not fit.success:return common,None
    delta=basis@fit.x[:-1]
    perturbed=f*(1+delta)
    metrics=c.integrate_colour(w,perturbed,mask_sky=False)
    old_mags=c.synthetic_gri(w,f,'panstarrs')
    new_mags=c.synthetic_gri(w,perturbed,'panstarrs')
    residual=float(np.max(np.abs(new_mags-old_mags)))
    boundary_rgb=c.XYZ_TO_RGB@(coeff.T@perturbed)
    boundary_error=float(abs(boundary_rgb[first]-boundary_rgb[second])/np.max(np.abs(boundary_rgb)))
    if residual>1e-7 or boundary_error>1e-6 or exact_max>fit.x[-1]+2e-8:
        raise AssertionError((residual,boundary_error,exact_max,fit.x[-1]))
    common.update(minimum_max_fractional_distortion=float(fit.x[-1]),
        supremum_lower_bound=float(fit.x[-1]),supremum_witness_upper_bound=exact_max,
        supremum_bound_gap=exact_max-float(fit.x[-1]),extrema_constraint_iterations=iteration+1,
        synthetic_gri_max_residual_mag=residual,
        fractional_colour_boundary_error=boundary_error,minimum_flux_multiplier=float((1+delta).min()),
        boundary_hex=metrics['hex'],boundary_duv=metrics['duv'],boundary_green_margin=metrics['green_channel_margin'])
    return common,dict(wavelength_angstrom=w,nominal_flux=f,distorted_flux=perturbed,fractional_distortion=delta,
                       spline_knots_angstrom=knots,spline_coefficients=fit.x[:-1])


def run():
    results=[];curves={};hashes={}
    for candidate in ['J0913+4434','J0429-0354']:
        path=ROOT/f'results/candidates/{candidate}_DESI_panstarrs.npz'
        hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        d=np.load(path)
        w,f,iv=c.clean_spectrum(d['wavelength_angstrom'],d['flux_calibrated'],d['inverse_variance'],mask_sky=True)
        original_mags=c.synthetic_gri(d['wavelength_angstrom'],d['flux_calibrated'],'panstarrs')
        cleaned_mags=c.synthetic_gri(w,f,'panstarrs')
        cleaning_delta=cleaned_mags-original_mags
        f=f/np.median(f[(w>5000)&(w<7000)])
        nominal=c.integrate_colour(w,f,mask_sky=False)
        for spacing in [400,800,1600]:
            for pair in ['G-R','G-B']:
                result,arrays=minimum_flip(w,f,spacing,pair)
                result.update(candidate=candidate,nominal_hex=nominal['hex'],nominal_duv=nominal['duv'],nominal_green_margin=nominal['green_channel_margin'])
                result.update(cleaned_minus_original_g_mag=float(cleaning_delta[0]),
                    cleaned_minus_original_r_mag=float(cleaning_delta[1]),
                    cleaned_minus_original_i_mag=float(cleaning_delta[2]),
                    cleaned_minus_original_g_r=float(cleaning_delta[0]-cleaning_delta[1]),
                    cleaned_minus_original_r_i=float(cleaning_delta[1]-cleaning_delta[2]))
                results.append(result)
                if arrays is not None:
                    outfile=OUT/f'{candidate}_gri_null_{spacing}A_{pair}.npz'
                    np.savez_compressed(outfile,**arrays)
                    if spacing==800:curves[(candidate,pair)]=arrays
                print(candidate,spacing,pair,result.get('minimum_max_fractional_distortion'),flush=True)
    table=pd.DataFrame(results);table.to_csv(OUT/'photometric_nullspace.csv',index=False)
    summary={'input_sha256':hashes,'method':'Minimum L-infinity multiplicative cubic-spline shape distortion; exact conservation of the CLEANED baseline Pan-STARRS gri synthetic photon fluxes; linear-sRGB equality boundary. Analytic polynomial extrema bracket the continuous supremum.',
             'important_limit':'Adversarial existence result under chosen spline spaces. NOT a measured DESI error, probability, confidence interval, physical abundance perturbation, or independent validation.',
             'scope':'Supremum norm across observed wavelength range, including wavelengths outside the CIE interval needed by the i-band anchor. Positive multipliers enforced.',
             'knot_spacing_note':'400/800/1600 Angstrom spacing are alternative sensitivity scenarios, not instrumental correlation lengths.',
             'three_band_inference':'Matching gri fluxes alone cannot constrain distortions in their null space. A relative spectral calibration constraint is additional information.',
             'baseline_note':'Invalid pixels and narrow sky masks are removed before defining the baseline. Its band fluxes differ slightly from the original full-grid DESI+PS1 product; these differences are reported per result. Constraints preserve synthetic baseline fluxes, not necessarily observed catalogue fluxes.',
             'results':results}
    (OUT/'photometric_nullspace.json').write_text(json.dumps(summary,indent=2)+'\n')
    def display_bins(w,f):
        edges=np.arange(3300,10601,20)
        ids=np.digitize(w,edges)
        bins=[ids==k for k in range(1,len(edges)) if np.any(ids==k)]
        return np.array([np.mean(w[b])/10 for b in bins]),np.array([np.mean(f[b]) for b in bins])
    fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True,layout='constrained')
    for i,candidate in enumerate(['J0913+4434','J0429-0354']):
        for pair,col in [('G-R','#156c96'),('G-B','#a04e34')]:
            if (candidate,pair) not in curves:continue
            a=curves[(candidate,pair)];x=a['wavelength_angstrom']/10
            axes[i,0].plot(x,a['fractional_distortion']*100,label=pair,color=col,lw=1.4)
            bx,by=display_bins(a['wavelength_angstrom'],a['distorted_flux'])
            axes[i,1].plot(bx,by,label=f'At {pair}=0',color=col,lw=1.2,alpha=.9)
        if (candidate,'G-R') in curves:
            a=curves[(candidate,'G-R')]
            bx,by=display_bins(a['wavelength_angstrom'],a['nominal_flux'])
            axes[i,1].plot(bx,by,color='#222222',lw=1.0,alpha=.8,label='Nominal DESI + PS1')
        axes[i,0].axhline(0,color='grey',lw=.7)
        axes[i,0].set_title(candidate+' — unconstrained shape modes')
        axes[i,0].set_ylabel('Multiplicative distortion (%)')
        axes[i,1].set_title('Same synthetic g, r, i fluxes; 20 Å display bins')
        axes[i,1].set_ylabel('Relative energy flux per wavelength')
        axes[i,1].set_ylim(-.15,3)
        for ax in axes[i]:
            ax.set_xlim(360,960);ax.grid(alpha=.15);ax.legend(fontsize=8)
    for ax in axes[-1]:ax.set_xlabel('Wavelength (nm)')
    fig.suptitle('How much smooth spectral distortion could erase green-channel dominance?\n800 Å spline knots; sensitivity experiment, not a calibration-error estimate',fontsize=13)
    fig.savefig(OUT/'photometric_nullspace.png',dpi=180)
    fig.savefig(OUT/'photometric_nullspace.svg')
    plt.close(fig)
    print(table[['candidate','spacing_A','colour_boundary','minimum_max_fractional_distortion','synthetic_gri_max_residual_mag']].to_string(index=False))


if __name__=='__main__':run()
