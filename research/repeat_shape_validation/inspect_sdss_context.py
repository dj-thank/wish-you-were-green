#!/usr/bin/env python3
"""Read original coadd context and, optionally, public Gaia/exposure headers."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime,timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import urllib.parse
import urllib.request
from astropy.io import fits
from astropy.coordinates import SkyCoord
from astropy.time import Time
import astropy.units as units
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CONTEXT=HERE/'context'
GAIA_QUERY="""SELECT g.source_id,g.ra,g.dec,g.ref_epoch,g.parallax,g.parallax_error,g.pmra,g.pmdec,g.phot_g_mean_mag,g.bp_rp,g.ruwe,g.phot_variable_flag,g.has_xp_continuous,g.duplicated_source,g.non_single_star,g.ipd_frac_multi_peak,v.classifier_name,v.best_class_name,v.best_class_score FROM gaiadr3.gaia_source AS g LEFT OUTER JOIN gaiadr3.vari_classifier_result AS v ON g.source_id=v.source_id WHERE g.source_id=3646912496889350784 OR 1=CONTAINS(POINT('ICRS',g.ra,g.dec),CIRCLE('ICRS',212.5239,-2.5835637,0.004166666666666667)) ORDER BY g.source_id"""


def sha(data):return hashlib.sha256(data).hexdigest()


def coadd_context(root=ROOT):
    m=json.loads((root/'research/repeat_shape_validation/inputs_manifest.json').read_text())
    pair=next(p for p in m['pairs'] if p['instrument']=='SDSS')
    result=[]
    for e in pair['epochs']:
        raw=gzip.decompress((root/e['path']).read_bytes());assert sha(raw)==e['uncompressed_sha256']
        with fits.open(io.BytesIO(raw)) as h:
            head=h[0].header;d=h[2].data
            exposure_names=[head[k] for k in head if k.startswith('EXPID')]
            science=sorted({int(x.split('-')[1]) for x in exposure_names})
            fields=['CLASS','SUBCLASS','Z','Z_ERR','ZWARNING','SN_MEDIAN_ALL','SN_MEDIAN','SPECPRIMARY','OBJTYPE','RUN2D','RUN1D']
            table={}
            for k in fields:
                if k in d.dtype.names:
                    value=d[k][0];table[k]=value.tolist() if hasattr(value,'tolist') else str(value)
            result.append(dict(row_index=e['row_index'],spectrum_id=e['exposure'],plate=head['PLATEID'],label_mjd=head['MJD'],
                contributing_mjds=[int(x) for x in head['MJDLIST'].split()],science_exposure_ids=science,n_physical_exposures=len(science),
                camera_exposure_ids=exposure_names,exptime_s=head['EXPTIME'],header={k:head.get(k) for k in ['PLUG_RA','PLUG_DEC','BUNIT','AIRMASS','SEEING','SEEING50','NEXP','NEXP_B1','NEXP_R1']},
                pipeline_classification=table,source_url=e['original_url'],raw_sha256=e['uncompressed_sha256']))
    a,b=result
    assert not set(a['science_exposure_ids'])&set(b['science_exposure_ids'])
    assert not set(a['contributing_mjds'])&set(b['contributing_mjds'])
    return result


def fetch(url,path,limit=None,extra_headers=None):
    start=datetime.now(timezone.utc).isoformat()
    request=urllib.request.Request(url,headers={'User-Agent':'wish-you-were-green public astronomy data validation',**(extra_headers or {})})
    with urllib.request.urlopen(request,timeout=45) as response:
        raw=response.read(limit) if limit else response.read()
        meta=dict(request_url=url,resolved_url=response.url,http_status=response.status,content_type=response.headers.get('Content-Type'),
            content_range=response.headers.get('Content-Range'),content_length_header=response.headers.get('Content-Length'),http_date=response.headers.get('Date'),
            started_utc=start,retrieved_utc=datetime.now(timezone.utc).isoformat(),saved_bytes=len(raw),sha256=sha(raw),requested_byte_limit=limit)
    path.write_bytes(raw)
    path.with_suffix(path.suffix+'.provenance.json').write_text(json.dumps(meta,indent=2)+'\n')
    return raw,meta


def parse_primary_header(raw):
    # The stored bytes are a bounded primary-header prefix, NOT an entire FITS.
    end=next((i+80 for i in range(0,len(raw)-79,80) if raw[i:i+8]==b'END     '),None)
    if end is None:raise ValueError('END card absent from saved 64 KiB prefix')
    return fits.Header.fromstring(raw[:end].decode('ascii'),sep='')


def download():
    CONTEXT.mkdir(exist_ok=True)
    (CONTEXT/'gaia_query.adql').write_text(GAIA_QUERY+'\n')
    gp=CONTEXT/'gaia_target_and_neighbours.csv'
    if not gp.exists():
        url='https://gea.esac.esa.int/tap-server/tap/sync?'+urllib.parse.urlencode(dict(REQUEST='doQuery',LANG='ADQL',FORMAT='csv',QUERY=GAIA_QUERY))
        raw,meta=fetch(url,gp)
        rows=list(csv.DictReader(io.StringIO(raw.decode())))
        assert sum(r['source_id']=='3646912496889350784' for r in rows)==1
        print(json.dumps({'gaia_rows':len(rows),'retrieved_utc':meta['retrieved_utc']}),flush=True)
    tasks=[(r['plate'],x) for r in coadd_context() for x in r['science_exposure_ids']]
    def one(task):
        plate,exp=task
        name=f'spCFrame-b1-{exp:08d}.fits'
        path=CONTEXT/(f'plate{plate}_'+name+'.header.bin')
        url=f'https://data.sdss.org/sas/dr17/eboss/spectro/redux/v5_13_2/{plate}/{name}'
        try:
            if not path.exists():raw,meta=fetch(url,path,65536,{'Range':'bytes=0-65535'})
            else:raw=path.read_bytes()
            h=parse_primary_header(raw)
            result=dict(plate=plate,science_exposure_id=exp,status='header_recovered',path=str(path.relative_to(ROOT)),sha256=sha(raw),source_url=url,
                header={k:h[k] for k in h if any(x in k for x in ['AIRMASS','SEEING','MJD','DATE-OBS','EXPT','TAI','ALT','AZ','HA','COFFSET','GUID','PRESS','HUMID','WIND'])})
        except Exception as exc:
            result=dict(plate=plate,science_exposure_id=exp,status='unavailable',source_url=url,error=type(exc).__name__+': '+str(exc))
        print(json.dumps({'exposure':exp,'status':result['status']}),flush=True)
        return result
    with ThreadPoolExecutor(max_workers=2) as ex:records=list(ex.map(one,tasks))
    (CONTEXT/'exposure_header_retrieval.json').write_text(json.dumps(records,indent=2)+'\n')


def collect(root=ROOT):
    directory=root/'research/repeat_shape_validation/context'
    out=dict(coadds=coadd_context(root),coadd_independence='Two different plate-MJD-fibre coadds with disjoint science exposures and disjoint contributing MJD sets; not two individual exposures or two single nights',
        classification_interpretation='Retained catalogue labels DZA (MWDD entries) and DAZ (direct SDSS selected entries) differ from generic SDSS pipeline STAR/F3-F5V template. Preserve this classification/provenance disagreement; these labels do not establish a CV, binary, or new classification',
        no_variability_or_calibration_error_distribution_inference=True)
    catalogue_path=root/'research/precision/flux_units/corrected_record_screen.csv.gz'
    with gzip.open(catalogue_path,'rt') as handle:
        catalogue=[{k:r[k] for k in ['row_index','source_id','wdid','spectype','teff','kind','source_url','star_page_url','flux_units_validated','flux_input_convention','usable_screen','identity_basis','sha256']}
                   for r in csv.DictReader(handle) if r['source_id']=='3646912496889350784']
    out['retained_catalogue_context']=dict(path=str(catalogue_path.relative_to(root)),sha256=sha(catalogue_path.read_bytes()),rows=catalogue,
        limits='Frozen catalogue metadata, including its DZA/DAZ ordering difference; no fresh atmospheric fit or resolved specialist classification is implied. Unresolved MWDD row 4267 contributes metadata only, never spectral flux to this experiment.')
    for coadd in out['coadds']:
        record=next(r for r in catalogue if int(r['row_index'])==coadd['row_index'])
        assert record['sha256']==coadd['raw_sha256']
        assert record['flux_units_validated']=='True' and record['flux_input_convention']=='flambda' and record['usable_screen']=='True'
    gp=directory/'gaia_target_and_neighbours.csv'
    if gp.exists():
        rows=list(csv.DictReader(io.StringIO(gp.read_text())));t=next(r for r in rows if r['source_id']=='3646912496889350784')
        for r in rows:
            dra=(float(r['ra'])-float(t['ra']))*np.cos(np.radians(float(t['dec'])))
            ddec=float(r['dec'])-float(t['dec'])
            r['separation_from_target_arcsec']=float(np.hypot(dra,ddec)*3600)
            r['G_flux_ratio_to_target']=float(10.**(-.4*(float(r['phot_g_mean_mag'])-float(t['phot_g_mean_mag']))))
        out.update(gaia_source=t,gaia_field_rows=rows,gaia_raw_sha256=sha(gp.read_bytes()),
            gaia_limits='NOT_AVAILABLE is not evidence of constant flux; no classifier/NSS entry is not evidence against binarity. A 15 arcsec Gaia field does not model spectroscopic PSF wings or unresolved companions.')
    ep=directory/'exposure_header_retrieval.json'
    if ep.exists():
        records=json.loads(ep.read_text())
        # Reparse every saved header prefix; the cached JSON alone is not evidence.
        for r in records:
            if r['status']!='header_recovered':continue
            raw=(root/r['path']).read_bytes();assert sha(raw)==r['sha256']
            h=parse_primary_header(raw)
            assert int(h['EXPOSURE'])==r['science_exposure_id']
            assert int(h['PLATEID'])==r['plate']
            for k,value in r['header'].items():assert h[k]==value
        out['exposure_headers']=records
        summaries=[]
        for coadd in out['coadds']:
            selected=[r for r in records if r['plate']==coadd['plate'] and r['status']=='header_recovered']
            assert sorted(r['science_exposure_id'] for r in selected)==coadd['science_exposure_ids']
            assert sorted({int(r['header']['MJD']) for r in selected})==coadd['contributing_mjds']
            summary=dict(plate=coadd['plate'],recovered_exposure_headers=len(selected))
            for field in ['AIRMASS','SEEING50','EXPTIME']:
                values=[r['header'][field] for r in selected if field in r['header']]
                summary[field]=dict(minimum=min(values),median=float(np.median(values)),maximum=max(values),entries=len(values))
            summary['SEEING50']['unit']='arcsec; original FITS keyword comment'
            summaries.append(summary)
        out['observing_condition_summary']=summaries
        if 'gaia_source' in out:
            target=out['gaia_source'];positions=[]
            for r in records:
                if r['status']!='header_recovered':continue
                obs=Time(float(r['header']['TAI-BEG'])/86400,format='mjd',scale='tai')
                delta=obs.tcb.jyear-float(target['ref_epoch'])
                pred_ra=float(target['ra'])+float(target['pmra'])*delta/(3.6e6*np.cos(np.radians(float(target['dec']))))
                pred_dec=float(target['dec'])+float(target['pmdec'])*delta/3.6e6
                coadd=next(c for c in out['coadds'] if c['plate']==r['plate'])
                plug=SkyCoord(ra=coadd['header']['PLUG_RA']*units.deg,dec=coadd['header']['PLUG_DEC']*units.deg)
                pos=SkyCoord(ra=pred_ra*units.deg,dec=pred_dec*units.deg)
                positions.append(dict(plate=r['plate'],science_exposure_id=r['science_exposure_id'],observed_jyear_tcb=float(obs.tcb.jyear),
                    predicted_ra_deg=pred_ra,predicted_dec_deg=pred_dec,separation_from_original_plug_arcsec=float(pos.separation(plug).arcsec)))
            parallax=float(target['parallax'])
            out['epoch_association']=dict(method='Linear Gaia proper-motion propagation with pmra=mu_alpha*cos(delta); original exposure TAI-BEG converted to TCB Julian year; no radial-velocity or astrometric-covariance model',
                exposures=positions,minimum_separation_arcsec=min(p['separation_from_original_plug_arcsec'] for p in positions),
                maximum_separation_arcsec=max(p['separation_from_original_plug_arcsec'] for p in positions),
                inverse_parallax_distance_pc=1000/parallax,parallax_signal_to_noise=parallax/float(target['parallax_error']),
                absolute_G_inverse_parallax_no_extinction=float(target['phot_g_mean_mag'])+5*np.log10(parallax)-10,
                limits='Position point estimates support a common intended target but do not measure wavelength-dependent aperture losses, unresolved companions, or identification probabilities; inverse-parallax distance and absolute magnitude are diagnostic proxies without extinction or a distance prior.')
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--download',action='store_true');args=ap.parse_args()
    if args.download:download()
    result=collect();(HERE/'sdss_context.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'coadd_MJD_sets':[r['contributing_mjds'] for r in result['coadds']],
       'gaia':result.get('gaia_source'),'headers_recovered':sum(r['status']=='header_recovered' for r in result.get('exposure_headers',[]))},indent=2))


if __name__=='__main__':main()
