from pathlib import Path
import json
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy import units as u
ROOT=Path(__file__).resolve().parent

def annotate(tab, *, legacy_unverified_units=False):
    ex=pd.read_csv(ROOT/'novelty/hollands2026_exclusions_unique.csv')
    ec=SkyCoord(ex.ra_deg.to_numpy()*u.deg,ex.dec_deg.to_numpy()*u.deg)
    tab=tab.copy()
    # An entirely withheld batch has no colour/coverage measurements. Keep
    # those rows for review while making every eligibility gate fail closed.
    for key, default in [('coverage_eligible', False),
                         ('cmf_min_coverage', np.nan),
                         ('largest_visible_gap_A', np.nan)]:
        if key not in tab:
            tab[key]=default
    valid=np.isfinite(pd.to_numeric(tab.ra_deg,errors='coerce'))&np.isfinite(pd.to_numeric(tab.dec_deg,errors='coerce'))
    cc=SkyCoord(tab.loc[valid,'ra_deg'].to_numpy()*u.deg,tab.loc[valid,'dec_deg'].to_numpy()*u.deg)
    ix,sep,_=cc.match_to_catalog_sky(ec)
    tab['nearest_published_name']='';tab['nearest_published_sep_arcsec']=np.nan;tab['nearest_published_hex']=''
    tab.loc[valid,'nearest_published_name']=ex.iloc[ix]['name'].to_numpy()
    tab.loc[valid,'nearest_published_sep_arcsec']=sep.arcsec
    tab.loc[valid,'nearest_published_hex']=ex.iloc[ix].srgb_hex.to_numpy()
    tab['known_hollands_colour']=tab.nearest_published_sep_arcsec<30
    tab['astrometric_match_review']=(tab.nearest_published_sep_arcsec>=30)&(tab.nearest_published_sep_arcsec<120)
    # A kind string cannot establish F_lambda: MWDD SDSS exports mix F_nu and
    # F_lambda. Current calculations carry explicit, provenance-backed status.
    if legacy_unverified_units:
        tab['source_format_screen_ok']=tab.kind.isin(['SDSS','DESI','Gaia_XP'])
    else:
        units=tab['flux_units_validated'].eq(True) if 'flux_units_validated' in tab else pd.Series(False,index=tab.index)
        tab['source_format_screen_ok']=units&tab.kind.isin(['SDSS','DESI','Gaia_XP'])
    tab['usable_screen']=valid&tab.source_format_screen_ok&tab.status.eq('ok')&tab.coverage_eligible.eq(True)&(tab.cmf_min_coverage>.995)&(tab.largest_visible_gap_A<150)
    if 'cal_max_residual_mag' in tab:
        tab['usable_screen'] &= (~tab.calibrated.eq(True)) | (tab.cal_max_residual_mag<.15)
        tab['usable_screen'] &= (~tab.calibrated.eq(True)) | (tab.cal_tilt_mag_per_1000A.abs()<.25)
    return tab

def summarize(tab):
    rows=[]
    selected=tab[tab.usable_screen&~tab.known_hollands_colour].copy()
    # Catalogue aliases are display names, not distinct objects. Keep legacy
    # name grouping only when no entity key is available, in its own namespace
    # so a missing key cannot merge with an unrelated explicit entity.
    entity=selected['entity_id'].astype('string') if 'entity_id' in selected else pd.Series(pd.NA,index=selected.index,dtype='string')
    selected['_entity_group']=[('entity',str(key)) if pd.notna(key) and str(key).strip()
                               else ('legacy_name',str(name)) for key,name in zip(entity,selected.wdid)]
    for _,g in selected.groupby('_entity_group'):
        good=g[g.status=='ok']
        if len(good)==0:continue
        ground=good[good.kind!='Gaia_XP']
        # Choose a representative by calibration, instrument, S/N and stable
        # provenance, never by the greatest apparent anomaly.
        good=good.copy()
        good['_instrument_preference']=good.kind.map({'DESI':0,'SDSS':1,'Gaia_XP':2}).fillna(9)
        if 'visible_median_pixel_snr' not in good:good['visible_median_pixel_snr']=np.nan
        best=good.sort_values(['calibrated','_instrument_preference','visible_median_pixel_snr','source_url'],
                             ascending=[False,True,False,True],na_position='last').iloc[0]
        xx=good.u1960.to_numpy(); yy=good.v1960.to_numpy()
        spread=float(np.max(np.sqrt((xx[:,None]-xx)**2+(yy[:,None]-yy)**2)))
        key=best.get('entity_id',None)
        rows.append({'entity_id':str(key) if pd.notna(key) and str(key).strip() else None,
                     'wdid':best.wdid,'source_id':str(best.source_id),'ra_deg':best.ra_deg,'dec_deg':best.dec_deg,
                     'spectype':best.spectype,'teff':best.teff,'spectra':len(good),'survey_kinds':','.join(sorted(set(good.kind))),
                     'ground_spectra':len(ground),'calibrated_spectra':int(good.calibrated.sum()),
                     'median_duv':float(good.duv.median()),'median_distance':float(good.distance_planck_uv.median()),
                     'min_distance':float(good.distance_planck_uv.min()),'max_between_spectra_uv':spread,
                     'green_spectra':int(good.green_dominant.sum()),'best_hex':best.hex,
                     'best_duv':best.duv,'best_kind':best.kind,'nearest_published_sep_arcsec':best.nearest_published_sep_arcsec,
                     'star_page_url':best.star_page_url})
    if not rows:
        return pd.DataFrame(columns=['entity_id','wdid','source_id','spectype','teff','spectra','survey_kinds','ground_spectra',
            'calibrated_spectra','median_duv','median_distance','min_distance','max_between_spectra_uv',
            'green_spectra','best_hex','best_duv','best_kind','nearest_published_sep_arcsec','star_page_url'])
    return pd.DataFrame(rows).sort_values(['ground_spectra','median_distance'],ascending=False)

if __name__=='__main__':
    source=ROOT/'research/precision/flux_units/corrected_record_screen.csv.gz'
    tab=annotate(pd.read_csv(source,dtype={'source_id':'string'},low_memory=False))
    destination=ROOT/'results/validated_screen';destination.mkdir(parents=True,exist_ok=True)
    summ=summarize(tab);summ.to_csv(destination/'all_object_candidates.csv',index=False)
    cols=['wdid','spectype','spectra','survey_kinds','median_duv','max_between_spectra_uv','green_spectra','best_hex','calibrated_spectra']
    print('total spectra',len(tab),'usable',sum(tab.usable_screen),'published matches',sum(tab.known_hollands_colour),'distinct unexcluded',len(summ))
    print('Green-colour follow-up candidates (Hollands comparison objects excluded)')
    print(summ[summ.green_spectra>0][cols].sort_values('median_duv',ascending=False).head(30).to_string(index=False))
    print('Other anomalous candidates with multiple records (independence requires review)')
    print(summ[(summ.spectra>=2)&(summ.median_distance>.01)&(summ.ground_spectra>0)][cols].sort_values('median_duv').head(30).to_string(index=False))
