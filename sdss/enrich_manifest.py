#!/usr/bin/env python3
"""Join authoritative PSF photometry without overwriting published tabulated values."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import numpy as np
import pandas as pd

BASE=Path(__file__).resolve().parent

def main():
    rows=json.loads((BASE/'manifest.json').read_text())
    folder=BASE/'photometry'
    embedded=json.loads((folder/'embedded_photometry.json').read_text())
    matches=json.loads((folder/'bestobjid_match.json').read_text())
    phot={r['spectrum_id']:r for r in embedded}
    for path in sorted(folder.glob('query-*.json'),key=lambda p:p.stat().st_mtime):
        if path.name.endswith('-provenance.json'):continue
        result=json.loads(path.read_text())
        provenance_path=path.with_name(path.stem+'-provenance.json')
        provenance=json.loads(provenance_path.read_text()) if provenance_path.exists() else {}
        if not isinstance(result,list):continue
        for table in result:
            if not isinstance(table,dict):continue
            for p in table.get('Rows',[]):
                if not isinstance(p,dict) or 'objID' not in p:continue
                objid=str(p['objID'])
                for spectrum_id in matches.get(objid,[]):
                    phot[spectrum_id]=dict(p,objID=objid,spectrum_id=spectrum_id,
                        source='SDSS_DR17_SkyServer_PhotoObjAll',source_url=provenance.get('url'),
                        source_path=str(path),source_sha256=provenance.get('sha256'))
    offsets=[]
    sky_offsets=[]
    for row in rows:
        p=phot.get(row['spectrum_id'])
        row['photometry_available']=p is not None
        if p:
            row['photometry_source']=p['source']
            row['photometry_source_url']=p.get('source_url')
            row['photometry_source_path']=p.get('source_path')
            row['photometry_sha256']=p.get('source_sha256')
            row['photometry_objid']=str(p['objID'])
            row['photometry_clean']=p.get('clean')
            row['photometry_type']=p.get('type')
            row['photometry_ra']=p.get('ra')
            row['photometry_dec']=p.get('dec')
            for band in 'ugriz':
                for source,target in [('psfMag','psf_mag'),('psfMagErr','psf_mag_err'),
                                      ('psfFlux','psf_flux_nanomaggies'),('psfFluxIvar','psf_flux_ivar'),
                                      ('extinction','extinction_mag'),('flags','phot_flags'),('flags2','phot_flags2')]:
                    if source+'_'+band in p:row[band+'_'+target]=p[source+'_'+band]
                val=row.get(band+'_psf_mag')
                if val is not None and row.get(band) is not None and 0<val<40 and 0<row[band]<40:
                    difference=row[band]-val
                    if abs(difference)>0.05:
                        offsets.append(dict(spectrum_id=row['spectrum_id'],name=row['name'],
                                            band=band,catalogue_mag=row[band],
                                            sdss_psf_mag=val,delta_mag=difference))
        if 'sdss_plug_ra' in row:
            dra=(row['ra']-row['sdss_plug_ra'])*np.cos(np.radians(row['dec']))
            ddec=row['dec']-row['sdss_plug_dec']
            separation=float(3600*np.hypot(dra,ddec))
            row['name_to_plug_offset_arcsec']=separation
            sky_offsets.append(separation)
    (BASE/'manifest_with_photometry.json').write_text(json.dumps(rows,indent=2,allow_nan=False))
    pd.DataFrame(rows).to_csv(BASE/'manifest_with_photometry.csv',index=False)
    report=dict(spectra=len(rows),successful_spectra=sum(r['status']=='ok' for r in rows),
        raw_bytes=sum(r.get('bytes',0) for r in rows if r['status']=='ok'),
        exact_unique_catalogue_names=len({r['name'] for r in rows}),
        with_authoritative_photometry=sum(r['photometry_available'] for r in rows),
        photometry_clean_counts=dict(Counter(str(r.get('photometry_clean')) for r in rows if r['photometry_available'])),
        photometry_source_counts=dict(Counter(r.get('photometry_source') for r in rows if r['photometry_available'])),
        catalogue_psf_differences_over_0p05mag=len(offsets),
        largest_catalogue_psf_differences=sorted(offsets,key=lambda r:abs(r['delta_mag']),reverse=True)[:30],
        max_name_to_fits_coordinate_difference_arcsec=max(sky_offsets),
        notes=[
            'Canonical u/g/r/i/z and *_err are retained from Kepler et al. 2019 Table 2; use *_psf_flux_nanomaggies, *_psf_flux_ivar or *_psf_mag and *_psf_mag_err for independently recovered photometry.',
            'PSF fluxes are in nanomaggies; their inverse variances are in inverse square nanomaggies. No extinction correction has been applied by these scripts.',
            'FITS coadd flux is in units 1e-17 erg/s/cm2/Angstrom at vacuum wavelengths. NPZ flux_flam is in erg/s/cm2/Angstrom and ivar is in inverse squared physical flux units; raw SDSS-unit arrays are also retained.',
            'Some published spectral types are explicitly uncertain or composite (colon, slash, +M etc.). Selection does not establish purity or novel colour.',
            '1397 spectra are observations, not necessarily distinct stars. Exact-name deduplication alone is insufficient when astrometry or rounding differs.',
            'Full FITS and NPZ arrays retain pixel masks and inverse variance. The parent analysis should assess valid visible-wavelength coverage and bad-pixel handling.',
            'Colour calculations and literature-novelty exclusion are performed by the parent workflow, not this acquisition script.'
        ],
        sources=[
            'https://doi.org/10.1093/mnras/stz960',
            'https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/486/2169/ReadMe',
            'https://www.sdss4.org/dr17/data_access/bulk/',
            'https://www.sdss4.org/dr17/spectro/spectro_basics/',
            'https://data.sdss.org/datamodel/files/SPECTRO_REDUX/specObj.html',
            'https://skyserver.sdss.org/dr17/Support/Api',
            'https://www.sdss4.org/dr17/algorithms/magnitudes/'
        ])
    (BASE/'qa_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ['notes','sources','largest_catalogue_psf_differences']},indent=2))

if __name__=='__main__':main()
