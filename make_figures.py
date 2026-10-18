"""Scientific figures generated from measured spectra and saved analyses."""
from pathlib import Path
import os,json
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'mpl-cache'))
import numpy as np
import pandas as pd
from project_io import read_dataframe
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Ellipse
import colour_pipeline as c
OUT=ROOT/'figures';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,
                     'figure.facecolor':'white','savefig.facecolor':'white','axes.titleweight':'semibold'})

def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=190,bbox_inches='tight')
    fig.savefig(OUT/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)

def selected():
    t=read_dataframe(ROOT/'results/candidates/validated_colours.csv',dtype={'source_id':'string'})
    choices=[('J0913+4434','DESI','panstarrs','Pale yellow-green candidate'),
             ('J0429-0354','DESI','panstarrs','Pale yellow-green candidate'),
             ('J1329+0033','DESI','panstarrs','Pink candidate'),
             ('J1323-0129','DESI','panstarrs','Unusual yellow candidate')]
    rows=[]
    for label,kind,system,description in choices:
        r=t[(t.candidate==label)&(t.kind==kind)&(t.cal_system==system)].iloc[0].to_dict()
        r['description']=description;rows.append(r)
    return pd.DataFrame(rows)

def swatches():
    t=selected()
    fig,axes=plt.subplots(2,2,figsize=(10.6,7.5))
    for ax,(_,r) in zip(axes.flat,t.iterrows()):
        ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
        ax.text(0,1,r['candidate'],size=17,weight='semibold',va='top')
        ax.text(0,.875,r['description'],size=11,color='#454b55',va='top')
        ax.add_patch(Rectangle((0,.21),1,.52,facecolor=r['hex'],edgecolor='#697480',lw=.8))
        ax.text(.5,.51,r['hex'],ha='center',va='center',size=20,weight='semibold')
        ax.text(.5,.36,f"x={r['x']:.4f}, y={r['y']:.4f}",ha='center',size=11)
        ax.text(0,.09,f"DESI + Pan-STARRS gri   |   Duv={r['duv']:+.4f}",size=10,va='center')
    fig.suptitle('New colour candidates in the public-spectrum search',size=19,x=.125,ha='left',y=1.025)
    fig.text(.125,-.015,'Computed sRGB / D65 patches, with the brightest channel scaled to 255. These are not photographs.\nKnown stars; candidate novelty concerns their human-vision colour. All results remain subject to calibration limits.',size=10,color='#4e5865')
    fig.subplots_adjust(hspace=.28,wspace=.17)
    save(fig,'candidate_colours')
    t.to_csv(ROOT/'results/headline_candidates.csv',index=False)

def bin_spectrum(w,f,width=25):
    edges=np.arange(3600,8350,width);ix=np.digitize(w,edges)
    xx=[];yy=[]
    for i in range(1,len(edges)):
        sel=ix==i
        if sel.sum():xx.append(np.mean(w[sel]));yy.append(np.mean(f[sel]))
    return np.array(xx),np.array(yy)

def ellipse(ax,uv,cov,color,label):
    vals,vecs=np.linalg.eigh(cov);order=np.argsort(vals)[::-1];vals,vecs=vals[order],vecs[:,order]
    angle=np.degrees(np.arctan2(vecs[1,0],vecs[0,0]))
    patch=Ellipse(uv,width=2*np.sqrt(max(vals[0],0)*5.991),height=2*np.sqrt(max(vals[1],0)*5.991),
                  angle=angle,facecolor=color,alpha=.13,edgecolor=color,lw=1)
    ax.add_patch(patch);ax.scatter(*uv,color=color,s=42,label=label,zorder=5)

def j0913():
    d=np.load(ROOT/'results/candidates/J0913+4434_DESI_panstarrs.npz')
    w=d['wavelength_angstrom'];f=d['flux_calibrated'];norm=np.median(f[(w>5300)&(w<5500)])
    ww,ff=bin_spectrum(w,f/norm)
    fig=plt.figure(figsize=(11.5,10))
    grid=fig.add_gridspec(2,2,height_ratios=[1.05,1],hspace=.36,wspace=.32)
    ax=fig.add_subplot(grid[0,:])
    ax.plot(ww/10,ff,color='#086788',lw=1.9,label='DESI, 25 A bins (display only)')
    for suffix,label,color,alpha in [('full','Gaia XP, all coefficients','#dd7a25',.38),('truncated','Gaia XP, recommended truncation','#9b3f90',.9)]:
        g=np.load(ROOT/f'mwdd/gaia_validation/j0913_{suffix}_1nm.npz')
        gw=g['wavelength_nm'];gf=g['flux_w_m2_nm'];gn=np.median(gf[(gw>530)&(gw<550)])
        ax.plot(gw,gf/gn,lw=1.1,color=color,alpha=alpha,label=label)
    ax.axvspan(575,605,color='#e4b951',alpha=.15)
    ax.annotate('Broad absorption near 589 nm',xy=(589,.48),xytext=(603,.17),arrowprops={'arrowstyle':'->','color':'#655846'},size=11)
    ax.set(xlim=(380,780),ylim=(-.25,2.25),xlabel='Wavelength (nm)',ylabel='Relative energy flux per wavelength',title='WD J0913+4434: the broad spectral structure persists across reconstructions')
    ax.legend(loc='upper right',fontsize=9,framealpha=.92)
    ax.grid(alpha=.13)
    ax2=fig.add_subplot(grid[1,0])
    uv=c._BB_UV;good=(uv[:,0]>.18)&(uv[:,0]<.225)&(uv[:,1]>.30)&(uv[:,1]<.355)
    ax2.plot(uv[good,0],uv[good,1],color='#293241',label='Blackbody locus',lw=1.5)
    vals=d['mc_xy_uv_duv_margin_delta_b'];ellipse(ax2,vals[:,2:4].mean(axis=0),np.cov(vals[:,2:4].T),'#086788','DESI + PS1: 95% statistical region')
    audit=json.loads((ROOT/'mwdd/gaia_validation/j0913_colour_covariance_audit.json').read_text())
    for tag,color,label in [('j0913_full_1nm.npz','#dd7a25','Gaia full: 95% coefficient covariance'),('j0913_truncated_1nm.npz','#9b3f90','Gaia truncated: 95% coefficient covariance')]:
        r=next(x for x in audit['results'] if x['spectrum']==tag)
        xyz=np.array(r['xyz_native']);cov=np.array(r['xyz_covariance_native']);xx,yy,zz=xyz;den=xx+15*yy+3*zz
        jac=np.array([[4*(den-xx),-60*xx,-12*xx],[-6*yy,6*(den-15*yy),-18*yy]])/den**2
        ellipse(ax2,[r['u1960'],r['v1960']],jac@cov@jac.T,color,label)
    ax2.set(xlim=(.184,.223),ylim=(.308,.346),xlabel='CIE 1960 u',ylabel='CIE 1960 v',title='Colour and its conditional uncertainty')
    ax2.legend(loc='lower left',fontsize=8,framealpha=.96);ax2.grid(alpha=.15)
    ax3=fig.add_subplot(grid[1,1])
    s=read_dataframe(ROOT/'results/candidates/calibration_sensitivity.csv')
    s=s[(s.candidate=='J0913+4434')&(s.kind=='DESI')&s.variant.str.startswith('additional_tilt')]
    for system,color in [('sdss','#725ac1'),('panstarrs','#086788')]:
        z=s[s.cal_system==system].copy();z['extra']=z.variant.str.extract(r'tilt_([+-][0-9.]+)')[0].astype(float)
        ax3.plot(z.extra,z.green_channel_margin,'o-',color=color,label='Anchor: '+('SDSS' if system=='sdss' else 'Pan-STARRS'))
    ax3.axhline(0,color='#60666e',ls='--',lw=1)
    ax3.text(-.095,.01,'Green channel exceeds both red and blue',size=8,color='#275b40')
    ax3.set(xlabel='Additional smooth tilt (mag per 1,000 A)',ylabel='Linear G minus max(R, B)',title='Sensitivity to calibration tilt')
    ax3.legend(fontsize=9);ax3.grid(alpha=.15)
    fig.text(.125,.014,'Gaia errors include the published coefficient covariance. DESI regions include pixel noise and photometric errors;\nunknown calibration and crowding systematics are not included. The extra-tilt plot is a sensitivity test, not an error estimate.',size=10,color='#4e5865')
    save(fig,'j0913_validation')

def population():
    t=read_dataframe(ROOT/'results/all_spectra_screen.csv',dtype={'source_id':'string'},low_memory=False)
    good=t[t.usable_screen & t.calibrated.fillna(False)].copy()
    good=good.sort_values('kind').drop_duplicates('wdid')
    fig,ax=plt.subplots(figsize=(10.4,7.3))
    ax.scatter(good.u1960,good.v1960,c=good.hex,s=13,linewidths=.18,edgecolors='#68727c',alpha=.7,
               label=f'One calibrated record per catalogue identifier (N={len(good):,})')
    ax.plot(c._BB_UV[:,0],c._BB_UV[:,1],color='#273442',lw=1.8,label='Blackbody locus, through the Rayleigh-Jeans limit')
    for (_,r),offset in zip(selected().iterrows(),[(-75,25),(-100,-24),(-95,-28),(20,5)]):
        ax.scatter(r.u1960,r.v1960,c=r.hex,s=145,edgecolor='#263241',lw=1.1,zorder=5)
        ax.annotate(r.candidate,(r.u1960,r.v1960),xytext=offset,textcoords='offset points',fontsize=11,weight='semibold',
                    arrowprops={'arrowstyle':'-','color':'#4e5a69'},bbox={'facecolor':'white','alpha':.88,'edgecolor':'none','pad':2})
    ax.set(xlim=(.15,.34),ylim=(.23,.385),xlabel='CIE 1960 u',ylabel='CIE 1960 v',
           title='Colour screening of public white-dwarf spectra')
    ax.legend(loc='lower right',fontsize=9);ax.grid(alpha=.14)
    fig.text(.125,-.005,'Exploratory sample selected for DQ/DZ classifications, with SDSS controls. This is not a volume-complete sample.\nColour points are measured spectra; calibration quality and repeated-observation checks determine candidate status.',size=10,color='#4e5865')
    save(fig,'survey_colour_plane')

def baselines():
    t=read_dataframe(ROOT/'results/mwdd_screen_annotated.csv',dtype={'source_id':'string'},low_memory=False)
    choices=[('J0851+1543','WD 0848+159','Gaia_XP','#F1FFF8','Observed spectrum closely reproduced'),
             ('J1011+2845','LP 315-42','SDSS','#FF8775','Observed spectrum closely reproduced'),
             ('J1351+2645','SDSS J135123.86+264546.5','SDSS','#F3FFD2','Model versus observed spectrum'),
             ('J1330+6435','WD 1328+648','SDSS','#DDFFB8','Low-S/N observation versus model')]
    fig,ax=plt.subplots(figsize=(10,5.6));ax.axis('off');ax.set(xlim=(0,1),ylim=(0,1))
    ax.text(.04,.98,'Validation against the published comparison paper',size=18,weight='semibold')
    ax.text(.39,.86,'Published colour',ha='center');ax.text(.61,.86,'This analysis',ha='center')
    rows=[]
    for i,(label,name,kind,known,note) in enumerate(choices):
        r=t[(t.wdid==name)&(t.kind==kind)].iloc[0];y=.67-i*.18
        ax.text(.02,y+.05,label,size=12,weight='semibold',va='center')
        for xpos,col in [(.29,known),(.51,r.hex)]:
            ax.add_patch(Rectangle((xpos,y),.2,.10,facecolor=col,edgecolor='#87919a',lw=.7));ax.text(xpos+.1,y+.05,col,ha='center',va='center',size=12)
        ax.text(.74,y+.065,note.replace(' versus ','\nversus '),size=9,va='center')
        rows.append({'candidate':label,'wdid':name,'kind':kind,'published_hex':known,'computed_hex':r.hex,'computed_duv':r.duv,'calibration':r.cal_system,'qualification':note})
    ax.text(.02,.01,'Published model spectra are not all identical to the available observations; discrepancies are retained, not tuned away.',size=9,color='#4e5865')
    save(fig,'baseline_reproduction')
    pd.DataFrame(rows).to_csv(ROOT/'results/baseline_reproduction.csv',index=False)

if __name__=='__main__':
    swatches();j0913();population();baselines()
    print('Figures written to',OUT)
