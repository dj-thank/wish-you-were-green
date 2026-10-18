"""Independent native-grid colour integration and shape audit for J0913+4434.

Input is downloaded public spectra supplied by the acquisition agent. This
script does not import the main colour pipeline. The Planck function is a
shape comparator, not an atmospheric fit or line-identification model.
"""
from pathlib import Path
import csv
import json
import os
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import minimize_scalar
os.environ.setdefault('MPLCONFIGDIR', '/tmp/wd-colour-novelty-mplconfig')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
CMF = np.genfromtxt(BASE/'reference/cie1931_2deg.csv', delimiter=',', names=True)
LW = CMF['wavelength_nm'] * 10
CM = np.stack([CMF[k] for k in ('xbar','ybar','zbar')], axis=1)
M = np.array([[3.2410,-1.5374,-0.4986],[-.9692,1.8760,.0416],[.0556,-.2040,1.0570]])


def integrate(w, f):
    order = np.argsort(w)
    w, f = w[order], f[order]
    mask = np.isfinite(w) & np.isfinite(f) & (w >= 3600) & (w <= 8300)
    w, f = w[mask], f[mask]
    response = np.column_stack([np.interp(w,LW,CM[:,i],left=0,right=0) for i in range(3)])
    xyz = np.trapezoid(f[:,None]*response,w,axis=0)
    xy = xyz[:2]/xyz.sum()
    uv = np.array([4*xyz[0],6*xyz[1]])/(xyz[0]+15*xyz[1]+3*xyz[2])
    rgb = M@xyz
    rgb /= rgb.max()
    display = np.where(rgb<=.0031308,12.92*rgb,1.055*np.maximum(rgb,0)**(1/2.4)-.055)
    hexc = '#'+''.join(f'{v:02X}' for v in np.rint(np.clip(display,0,1)*255).astype(int))
    return dict(xy=xy,uv=uv,rgb=rgb,hex=hexc)


def planck(w, temp):
    lam = np.asarray(w)*1e-10
    return lam**-5 / np.expm1(.01438776877 / (lam * temp))


def colour_metrics(w,f):
    c = integrate(w,f)
    def objective(logt):
        uv = integrate(LW,planck(LW,10**logt))['uv']
        return np.sum((uv-c['uv'])**2)
    opt = minimize_scalar(objective,bounds=(3,8),method='bounded',options={'xatol':1e-10})
    uvp = integrate(LW,planck(LW,10**opt.x))['uv']
    rj = integrate(LW,LW**-4)['uv']
    dist = float(np.sqrt(min(opt.fun,np.sum((rj-c['uv'])**2))))
    out = {k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in c.items()}
    out.update(distance1960=dist,nearest_blackbody_k=float(10**opt.x),
               green_over_red=float(c['rgb'][1]-c['rgb'][0]),
               green_over_blue=float(c['rgb'][1]-c['rgb'][2]))
    return out


def narrow_sky_mask(w,f):
    ok = np.ones(len(w),dtype=bool)
    for a,b in [(5565,5588),(5885,5902),(6292,6308),(6355,6372)]:
        ok &= ~((w>=a)&(w<=b))
    return np.interp(w,w[ok],f[ok])


def shape_ratio(w,f):
    """Depression around Na-D vs adjacent broad sidebands; not equivalent width."""
    edges=np.arange(4000,7501,25)
    centres=(edges[:-1]+edges[1:])/2
    means=np.array([np.mean(f[(w>=a)&(w<b)]) for a,b in zip(edges[:-1],edges[1:])])
    mask=np.isfinite(means)
    centres,means=centres[mask],means[mask]
    # A simple continuum across widely spaced brackets can itself be curved.
    lo=np.mean(means[(centres>=5350)&(centres<5550)])
    hi=np.mean(means[(centres>=6350)&(centres<6550)])
    cont=np.interp(centres,[5450,6450],[lo,hi])
    trough=np.mean(means[(centres>=5750)&(centres<6050)]/cont[(centres>=5750)&(centres<6050)])
    return centres,means,float(trough)


def broad_window_interpolation(w, f, lo, hi):
    """An artificial shape diagnostic, not a sodium-removal atmosphere model."""
    out = f.copy()
    left = np.mean(f[(w >= lo-100) & (w <= lo)])
    right = np.mean(f[(w >= hi) & (w <= hi+100)])
    mask = (w >= lo-50) & (w <= hi+50)
    out[mask] = np.interp(w[mask], [lo-50, hi+50], [left, right])
    return out


def main():
    source_specs={
       'DESI': '191c0043f1e3020902d0ec3e',
       'Gaia XP': '7820a93754d6f6ddb733216e',
    }
    metrics={}
    replacements=[]
    fig,ax=plt.subplots(figsize=(11,5.5),layout='constrained')
    for label,key in source_specs.items():
        spec=np.load(BASE/'mwdd/parsed'/f'{key}.npz')
        w,f=spec['wavelength_angstrom'],spec['flux_original']
        good=np.isfinite(w)&np.isfinite(f)
        w,f=w[good],f[good]
        f=f/np.median(f[(w>=5350)&(w<=5550)])
        no_sky=narrow_sky_mask(w,f)
        for variant,flux in [('unmodified',f),('narrow_sky_interpolated',no_sky)]:
            metrics[label+' '+variant]=colour_metrics(w,flux)
        for lo,hi in [(5550,6250),(5500,6300),(5600,6200)]:
            artificial=broad_window_interpolation(w,no_sky,lo,hi)
            replacements.append(dict(source=label,
                artificial_replacement_angstrom=[lo-50,hi+50],
                metrics=colour_metrics(w,artificial)))
        centres,means,trough=shape_ratio(w,no_sky)
        metrics[label+' broad_depression']={'mean_5750_6050_over_5450_6450_linear_continuum':trough,
            'caution':'Phenomenological flux depression only; sidebands may contain metal absorption. Not an elemental abundance or a measured Na equivalent width.'}
        ax.plot(centres,means,label=label+' (25 Angstrom bins)',lw=1.7)
    wb=np.linspace(3800,7700,600)
    bb=planck(wb,4662);bb/=np.median(bb[(wb>=5350)&(wb<=5550)])
    ax.plot(wb,bb,'--',color='.5',label='4662 K blackbody, shape reference')
    for wl,name in [(3934,'Ca II'),(4227,'Ca I'),(5175,'Mg I'),(5893,'Na I')]:
        ax.axvline(wl,color='.8',lw=.7)
        ax.text(wl,2.05,name,rotation=90,va='top',ha='right',fontsize=9)
    ax.set(xlim=(3800,7700),ylim=(-.1,2.1),xlabel='Wavelength (Angstrom)',ylabel='Relative F_lambda, normalized at 5350-5550 Angstrom',
           title='WDJ091336.37+443405.41 / Gaia DR3 818833831355548928')
    ax.legend(loc='upper right',fontsize=9)
    fig.savefig(OUT/'j0913_independent_spectral_shape.png',dpi=180)
    (OUT/'j0913_independent_color_metrics.json').write_text(json.dumps(metrics,indent=2))
    (OUT/'j0913_broad_window_interpolation.json').write_text(json.dumps(dict(
        caution='Artificial interpolation diagnostic only. This is not a physical sodium-removal atmosphere model and does not measure Na abundance. It changes one broad window while holding the rest of the observed spectrum fixed.',
        results=replacements),indent=2))
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':main()
