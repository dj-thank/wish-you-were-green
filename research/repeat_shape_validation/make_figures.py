#!/usr/bin/env python3
"""Figures from frozen repeat-shape results; no recalculation of science."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/wish-green-repeat-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import BSpline

HERE=Path(__file__).resolve().parent
OUT=HERE/'figures'
COLOURS={'archive':'#284b70','common_first_gri_correction':'#759442','separate_fits_shared_gri_anchors':'#b04742'}
LABELS={'archive':'Survey archive','common_first_gri_correction':'One correction applied to both','separate_fits_shared_gri_anchors':'Separate fits to shared gri'}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    data=json.loads((HERE/'analysis_results.json').read_text())
    context=json.loads((HERE/'sdss_context.json').read_text())
    plt.rcParams.update({'font.size':10,'axes.titlesize':11,'axes.labelsize':10,'legend.fontsize':8,'figure.facecolor':'white','axes.spines.top':False,'axes.spines.right':False})
    products=[]
    def save(fig,stem,kind,ids):
        fig.savefig(OUT/(stem+'.png'),dpi=145)
        fig.savefig(OUT/(stem+'.svg'))
        plt.close(fig)
        products.append(dict(stem=stem,kind=kind,pair_ids=ids,png_sha256=sha(OUT/(stem+'.png')),svg_sha256=sha(OUT/(stem+'.svg'))))
    for pair in data['pairs']:
        archive=pair['states']['archive'];central=archive['spline_fits'][1]
        x=np.array(central['bin_center_A']);low=pair['common_samples']['wavelength_min_A'];high=pair['common_samples']['wavelength_max_A']
        fig,axes=plt.subplots(2,2,figsize=(14,9.5))
        ax=axes[0,0]
        if pair['instrument']=='SDSS':
            epoch_labels=['Coadd 4038: MJDs 55362, 55363','Coadd 4035: MJDs 55364, 55365, 55383']
            subtitle='Two disjoint coadd sets: five nights, 18 physical exposures; 100 Å means'
        else:
            epoch_labels=[f"NIGHT {e['night']} / EXPID {e['exposure']}" for e in pair['observations']]
            subtitle='Two distinct observing nights; common native-grid masks; 100 Å means'
        for y,label,color in zip([central['reference_bin_flux'],central['second_bin_flux']],epoch_labels,['#284b70','#c4722d']):
            ax.plot(x,y,'o-',ms=2.5,lw=1.2,label=label,color=color)
        ax.axhline(0,lw=.6,color='.7');ax.axvspan(6500,7100,color='.9',label='Mean-normalization window')
        ax.set(title='A. Survey-calibrated input shapes',ylabel='Relative Fλ (window mean = 1)',xlim=(low,high));ax.legend()
        ax=axes[0,1]
        ax.errorbar(x,central['bin_difference'],yerr=central['bin_difference_pixel_sigma'],fmt='.',ms=3,color='.5',ecolor='.8',label='Observed difference; pixel-noise bars')
        ax.plot(x,central['fitted_bin_difference'],color='#284b70',lw=1.6,label='800 Å smooth multiplicative projection')
        ax.axhline(0,color='.3',lw=.7);ax.set(title='B. Second − first, after the same normalization',ylabel='Δ relative Fλ',xlim=(low,high));ax.legend()
        ax=axes[1,0]
        dense=np.linspace(low,high,2000)
        for fit,style in zip(archive['spline_fits'],[':','-','--']):
            ax.plot(dense,100*BSpline(fit['knots_A'],fit['coefficients'],3)(dense),style,lw=1.5,label=f"{int(fit['spacing_A'])} Å knots",color={400:'#888888',800:'#284b70',1600:'#57989a'}[int(fit['spacing_A'])])
        mc=central['pixel_noise_perturbation'];q=np.array(mc['spline_at_bin_centers_quantiles_16_50_84'])
        ax.fill_between(x,100*q[0],100*q[2],color='#284b70',alpha=.15,label='800 Å: 16–84% pixel-noise perturbations')
        if 'separate_fits_shared_gri_anchors' in pair['states']:
            fit=pair['states']['separate_fits_shared_gri_anchors']['spline_fits'][1]
            ax.plot(dense,100*BSpline(fit['knots_A'],fit['coefficients'],3)(dense),color='#b04742',lw=1.2,label='800 Å after separate shared-gri fits')
        ax.axhline(0,color='.3',lw=.7);ax.set(title='C. Descriptive fractional shape projection',ylabel='Fitted multiplicative change (%)',xlabel='Vacuum wavelength (Å)',xlim=(low,high));ax.legend(loc='best')
        if pair['label']=='J1105+7247':
            ax.text(.98,.08,'Low blue flux: amplitudes depend strongly on the spline space.\nSome unconstrained fits have nonpositive multipliers.',ha='right',va='bottom',transform=ax.transAxes,fontsize=8,color='#b04742')
        ax=axes[1,1]
        for offset,(state,row) in zip([-.16,0,.16],pair['states'].items()):
            d=row['photometry']['second_minus_first_mag'];positions=[];values=[]
            for i,b in enumerate('griz'):
                if b in d:positions.append(i+offset);values.append(d[b])
            ax.plot(positions,values,'o-',ms=4,color=COLOURS[state],lw=1.2,label=LABELS[state])
            if state=='archive':
                for i,b in enumerate('griz'):
                    if b in d:
                        q=mc['band_differences'][b]['quantiles_16_50_84_mag']
                        ax.plot([i+offset]*2,[q[0],q[2]],color=COLOURS[state],lw=1.5)
        ax.axhline(0,color='.4',lw=.7);ax.set_xticks(range(4),list('griz'));ax.set(xlim=(-.5,3.5),title='D. Synthetic PS1 differences',ylabel='Δ magnitude (second − first; normalized)',xlabel='Passband');ax.legend()
        if pair['label']=='J1329+0033':
            ax.text(.98,.96,'i, z and full colour unavailable:\nsecond Z camera entirely masked',ha='right',va='top',transform=ax.transAxes,fontsize=9,color='#b04742')
        for ax in axes.ravel():ax.grid(alpha=.17)
        fig.suptitle(pair['label']+' — '+pair['instrument']+' repeated-observation shape comparison',fontsize=15,y=.984)
        fig.text(.5,.953,subtitle,ha='center',fontsize=10)
        fig.text(.5,.017,'Signed flux retained. Shared anchors correlate calibration information. Shape amplitudes and noise perturbations are not a calibration-error distribution or a variability detection.',ha='center',fontsize=8.5)
        # Fixed margins keep the left and middle y labels visible even for the
        # unusually large signed SDSS/J1105 ranges; no data-dependent cropping.
        fig.subplots_adjust(left=.10,right=.985,bottom=.11,top=.865,wspace=.24,hspace=.34)
        save(fig,pair['pair_id'],'four-panel observation/shape/photometry comparison',[pair['pair_id']])
    fig,axes=plt.subplots(1,2,figsize=(14,6.8))
    pairs=data['pairs'];xx=np.arange(len(pairs))
    for shift,state in zip([-.2,0,.2],COLOURS):
        y=[100*p['states'][state]['spline_fits'][1]['uniform_wavelength_rms_fraction'] if state in p['states'] else np.nan for p in pairs]
        axes[0].plot(xx+shift,y,'o',label=LABELS[state],color=COLOURS[state])
    for i,p in enumerate(pairs):
        q=p['states']['archive']['spline_fits'][1]['pixel_noise_perturbation']['rms_quantiles_16_50_84_fraction']
        axes[0].plot([i-.2]*2,[100*q[0],100*q[2]],color=COLOURS['archive'],lw=2)
    axes[0].set(ylabel='800 Å spline RMS over common wavelength domain (%)',title='Normalization and calibration treatment matter')
    for shift,bands,color in [(-.10,'gri','#7b8fa1'),(.10,'griz','#284b70')]:
        vals=[]
        for p in pairs:
            dec=next((d for d in p['states']['archive']['spline_fits'][1]['decompositions'] if d['bands']==bands),None)
            vals.append(100*dec['null_rms_fraction'] if dec else np.nan)
        axes[1].bar(xx+shift,vals,width=.18,label=bands+' synthetic-flux null component',color=color)
    axes[1].set(ylabel='Uniform-wavelength RMS of null component (%)',title='Broadband integrals leave shape directions unmeasured');axes[1].legend(loc='upper left')
    for ax in axes:
        ax.set_xticks(xx,[p['label']+('*' if p['label']=='J1329+0033' else '') for p in pairs],rotation=22,ha='right');ax.grid(axis='y',alpha=.2)
    fig.suptitle('Five purposively selected repeat pairs — descriptive projections, not an instrument population',fontsize=14)
    hh,ll=axes[0].get_legend_handles_labels();fig.legend(hh,ll,loc='upper center',bbox_to_anchor=(.5,.927),ncol=3)
    fig.text(.5,.02,'*J1329 uses only common B/R coverage, so its domain differs and gri/griz-null results are withheld. Bars on the left propagate supplied independent pixel noise only.\nJ1105 is weakly constrained in its low-flux blue region. J1410 is two disjoint SDSS coadds, not two single-night exposures.',ha='center',fontsize=9)
    fig.tight_layout(rect=(.01,.10,.99,.865))
    save(fig,'repeat_shape_summary','five-pair RMS and synthetic-photometry-null comparison',[p['pair_id'] for p in pairs])
    fig,axes=plt.subplots(1,2,figsize=(12,4.9))
    for plate,color in [(4038,'#284b70'),(4035,'#c4722d')]:
        rows=[r for r in context['exposure_headers'] if r['plate']==plate and r['status']=='header_recovered']
        time=np.array([r['header']['TAI-BEG']/86400-55362 for r in rows])
        for ax,field in zip(axes,['SEEING50','AIRMASS']):
            ax.plot(time,[r['header'][field] for r in rows],'o',color=color,label=f'Plate {plate}: {len(rows)} physical exposures')
            ax.set(xlabel='Exposure TAI MJD − 55362',ylabel='SEEING50 (arcsec)' if field=='SEEING50' else field);ax.grid(alpha=.2);ax.legend()
    fig.suptitle('J1410−0235: conditions vary within the two SDSS coadd sets',fontsize=14)
    fig.text(.5,.018,'Original b1 camera headers, retrieved as 64 KiB byte ranges; paired r1 records are the same physical exposures.\nSeeing/airmass differences motivate aperture and calibration checks; these headers do not quantitatively explain the colour discrepancy.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.13,1,.91));save(fig,'sdss_exposure_conditions','18 original exposure-header conditions',['sdss_3646912496889350784'])
    manifest=dict(input_sha256={p.name:sha(p) for p in [HERE/'analysis_results.json',HERE/'sdss_context.json',HERE/'make_figures.py']},figures=products)
    (HERE/'figures_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'figures':len(products),'formats':['png','svg']}))


if __name__=='__main__':main()
