from pathlib import Path
import json
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy import units as u
ROOT=Path(__file__).resolve().parent

def annotate(tab):
    ex=pd.read_csv(ROOT/'novelty/hollands2026_exclusions_unique.csv')
    ec=SkyCoord(ex.ra_deg.to_numpy()*u.deg,ex.dec_deg.to_numpy()*u.deg)
    tab=tab.copy()
    valid=np.isfinite(pd.to_numeric(tab.ra_deg,errors='coerce'))&np.isfinite(pd.to_numeric(tab.dec_deg,errors='coerce'))
    cc=SkyCoord(tab.loc[valid,'ra_deg'].to_numpy()*u.deg,tab.loc[valid,'dec_deg'].to_numpy()*u.deg)
    ix,sep,_=cc.match_to_catalog_sky(ec)
    tab['nearest_published_name']='';tab['nearest_published_sep_arcsec']=np.nan;tab['nearest_published_hex']=''
    tab.loc[valid,'nearest_published_name']=ex.iloc[ix]['name'].to_numpy()
    tab.loc[valid,'nearest_published_sep_arcsec']=sep.arcsec
    tab.loc[valid,'nearest_published_hex']=ex.iloc[ix].srgb_hex.to_numpy()
    tab['known_hollands_colour']=tab.nearest_published_sep_arcsec<30
    tab['astrometric_match_review']=(tab.nearest_published_sep_arcsec>=30)&(tab.nearest_published_sep_arcsec<120)
    # The remaining legacy/ground exports can contain F_nu or continuum-normalised
    # spectra. Their unverified flux-density convention is not discovery evidence.
    tab['source_format_screen_ok']=tab.kind.isin(['SDSS','DESI','Gaia_XP'])
    tab['usable_screen']=valid&tab.source_format_screen_ok&tab.coverage_eligible.fillna(False)&(tab.cmf_min_coverage>.995)&(tab.largest_visible_gap_A<150)
    if 'cal_max_residual_mag' in tab:
        tab['usable_screen'] &= (~tab.calibrated.fillna(False)) | (tab.cal_max_residual_mag<.15)
        tab['usable_screen'] &= (~tab.calibrated.fillna(False)) | (tab.cal_tilt_mag_per_1000A.abs()<.25)
    return tab

def summarize(tab):
    rows=[]
    for name,g in tab[tab.usable_screen&~tab.known_hollands_colour].groupby('wdid'):
        good=g[g.status=='ok']
        if len(good)==0:continue
        ground=good[good.kind!='Gaia_XP']
        best=good.sort_values(['calibrated','distance_planck_uv'],ascending=[False,False]).iloc[0]
        xx=good.u1960.to_numpy(); yy=good.v1960.to_numpy()
        spread=float(np.max(np.sqrt((xx[:,None]-xx)**2+(yy[:,None]-yy)**2)))
        rows.append({'wdid':name,'source_id':str(best.source_id),'ra_deg':best.ra_deg,'dec_deg':best.dec_deg,
                     'spectype':best.spectype,'teff':best.teff,'spectra':len(good),'survey_kinds':','.join(sorted(set(good.kind))),
                     'ground_spectra':len(ground),'calibrated_spectra':int(good.calibrated.sum()),
                     'median_duv':float(good.duv.median()),'median_distance':float(good.distance_planck_uv.median()),
                     'min_distance':float(good.distance_planck_uv.min()),'max_between_spectra_uv':spread,
                     'green_spectra':int(good.green_dominant.sum()),'best_hex':best.hex,
                     'best_duv':best.duv,'best_kind':best.kind,'nearest_published_sep_arcsec':best.nearest_published_sep_arcsec,
                     'star_page_url':best.star_page_url})
    return pd.DataFrame(rows).sort_values(['ground_spectra','median_distance'],ascending=False)

if __name__=='__main__':
    tab=annotate(pd.read_csv(ROOT/'results/mwdd_screen.csv',dtype={'source_id':'string'}))
    tab.to_csv(ROOT/'results/mwdd_screen_annotated.csv',index=False)
    summ=summarize(tab);summ.to_csv(ROOT/'results/mwdd_object_candidates.csv',index=False)
    cols=['wdid','spectype','spectra','survey_kinds','median_duv','max_between_spectra_uv','green_spectra','best_hex','calibrated_spectra']
    print('total spectra',len(tab),'usable',sum(tab.usable_screen),'published matches',sum(tab.known_hollands_colour),'distinct unexcluded',len(summ))
    print('NEW green candidates')
    print(summ[summ.green_spectra>0][cols].sort_values('median_duv',ascending=False).head(30).to_string(index=False))
    print('NEW other anomalous with independent spectra')
    print(summ[(summ.spectra>=2)&(summ.median_distance>.01)&(summ.ground_spectra>0)][cols].sort_values('median_duv').head(30).to_string(index=False))
