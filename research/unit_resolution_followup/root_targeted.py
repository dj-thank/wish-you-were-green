#!/usr/bin/env python3
"""Original-pixel context for five features actually flagged by contact-sheet review."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from research.unit_resolution_followup.compact_inputs import CompactInputs

ROWS=(6462,6652,6951,7993,8040)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def compute(root=ROOT):
    root=Path(root);b=root/'research/unit_resolution_followup';store=CompactInputs(root)
    overlay={r['mwdd_row_index']:r for r in json.loads((b/'overlay_registry.json').read_text())['records']}
    table=pd.read_csv(b/'newly_resolved_record_screen.csv.gz',dtype={'source_id':str},low_memory=False).set_index('row_index')
    out=[];curves={}
    for i in ROWS:
        e=overlay[i];r=table.loc[i];v=store.load(e['external_reference_id']);w,f,iv=v['wave'],v['flux'],v['ivar']
        visible=(w>=3600)&(w<=8300);valid=visible&np.isfinite(f)&np.isfinite(iv)&(iv>0)
        anchor=valid&(w>=6500)&(w<=7100);scale=float(np.mean(f[anchor]));assert scale>0
        corr=10**(-.4*(float(r.cal_offset_mag)+float(r.cal_tilt_mag_per_1000A)*(w-6200)/1000)) if r.calibrated else np.ones_like(w)
        ref=store.entries[e['external_reference_id']]
        bandmeans={}
        for lo,hi in [(5600,5750),(5800,5950),(6000,6150),(6200,6350)]:
            keep=valid&(w>=lo)&(w<hi)
            bandmeans[f'{lo}_{hi}']={'valid_pixels':int(keep.sum()),'mean_raw_over_grey_anchor':float(np.mean(f[keep])/scale) if keep.any() else None,'mean_after_same_existing_correction_over_raw_grey_anchor':float(np.mean((f*corr)[keep])/scale) if keep.any() else None}
        row={'row_index':i,'source_id':str(r.source_id),'wdid':str(r.wdid),'catalogue_spectype':str(r.spectype),
             'star_page_url':str(r.star_page_url),'reference_key':e['external_reference_id'],
             'reference_url':ref['source_url'],'reference_original_sha256':ref['raw_sha256'],
             'original_automatic_classification':ref['hdu2_quality'],
             'visible_pixels':int(visible.sum()),'visible_nonpositive_or_invalid_ivar':int((visible&~valid).sum()),
             'visible_AND_nonzero':int((visible&(v['and_mask']!=0)).sum()),
             'visible_OR_nonzero':int((visible&(v['or_mask']!=0)).sum()),
             'max_positive_ivar_gap_A':float(np.diff(w[valid]).max()),
             'reference_median_pixel_snr':float(np.median(f[valid]*np.sqrt(iv[valid]))),
             'existing_offset_mag':float(r.cal_offset_mag),'existing_tilt_mag_per_1000A':float(r.cal_tilt_mag_per_1000A),
             'window_means_not_arm_step_fits':bandmeans,
             'limits':'Same original observation; positive IVAR does not establish correct sky subtraction, fibre centring, catalogue association, line identity or atmosphere physics. Catalogue spectral types and automatic classes are reported as distinct recorded labels. Window means span real absorption structure and are not a fitted camera mismatch or a calibration uncertainty.'}
        out.append(row);curves[str(i)]={'wavelength_A':w,'raw_over_grey_anchor':f/scale,'existing_correction_over_raw_grey_anchor':f*corr/scale,'positive_ivar':valid,'and_nonzero':v['and_mask']!=0,'or_nonzero':v['or_mask']!=0}
    return out,curves

def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    b=ROOT/'research/unit_resolution_followup';dest=b/'root_targeted';dest.mkdir(exist_ok=True)
    rows,curves=compute();fig,axes=plt.subplots(5,2,figsize=(14,17),layout='constrained')
    for line,r in enumerate(rows):
        v=curves[str(r['row_index'])];w=v['wavelength_A']/10;f=v['raw_over_grey_anchor'];valid=v['positive_ivar']
        for col,extent in enumerate([(360,830),(370,720) if r['row_index']==6462 else (550,645)]):
            ax=axes[line,col];keep=(w>=extent[0])&(w<=extent[1]);ok=keep&valid
            ax.plot(w[keep],f[keep],color='#aeb5bf',lw=.5,label='All native flux')
            ax.scatter(w[ok],f[ok],s=2,color='#245a7c',label='Positive IVAR')
            bad=keep&~valid;ax.scatter(w[bad],f[bad],s=14,marker='x',color='#c33f38',label='No positive IVAR')
            flagged=ok&v['and_nonzero'];ax.scatter(w[flagged],f[flagged],s=11,facecolors='none',edgecolors='#da9529',label='Nonzero AND')
            ax.plot(w[keep],v['existing_correction_over_raw_grey_anchor'][keep],color='#437f52',lw=.6,alpha=.8,label='Same existing correction')
            ax.axhline(0,color='#777777',lw=.5);ax.set_xlim(extent);ax.set_xlabel('Vacuum wavelength (nm)');ax.set_ylabel('Fλ / raw 650–710 nm mean');ax.grid(alpha=.15)
            ax.set_title(f"row {r['row_index']} | {r['catalogue_spectype']} catalogue / {r['original_automatic_classification']['CLASS']} automatic\nS/N {r['reference_median_pixel_snr']:.1f}; IVAR-invalid {r['visible_nonpositive_or_invalid_ivar']}/{r['visible_pixels']}",fontsize=10)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=5,fontsize=10)
    fig.suptitle('Five visually flagged spectra: native support and retained classification conflicts\nFull native values, including negative flux; no line clipping or claimed new line identification',fontsize=14)
    fig.savefig(dest/'original_pixel_context.png',dpi=145);plt.close(fig)
    source_paths=[Path(__file__),b/'compact_manifest.json',b/'overlay_registry.json',b/'newly_resolved_record_screen.csv.gz',b/'root_visual_review_21_30.csv']
    result={'rows':rows,'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in source_paths},'figure':'original_pixel_context.png','figure_sha256':sha(dest/'original_pixel_context.png')}
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps([{k:r[k] for k in ['row_index','catalogue_spectype','visible_nonpositive_or_invalid_ivar','max_positive_ivar_gap_A','reference_median_pixel_snr']} for r in rows],indent=2))

if __name__=='__main__':main()
