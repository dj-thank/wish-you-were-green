"""Explicit new-evidence overlay; the historical core registry is unchanged."""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from flux_conventions import as_flux_lambda as base_as_flux_lambda, UnverifiedFluxConvention
C_ANGSTROM_PER_SECOND=2.99792458e18


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def create():
    basepath=ROOT/'research/precision/flux_convention_evidence.json'
    base=json.loads(basepath.read_text());previous={r['mwdd_sha256']:r for r in base['records']}
    evidencepath=OUT/'unit_evidence_all.json';evidence=json.loads(evidencepath.read_text())
    with gzip.open(ROOT/'results/screen_input_mwdd.json.gz','rt') as stream:frozen=json.load(stream)
    entries=[]
    for r in evidence['records']:
        if r['convention']=='unresolved':continue
        original=frozen[r['mwdd_row_index']]
        assert previous[r['mwdd_sha256']]['convention']=='unresolved'
        assert original['sha256']==r['mwdd_sha256']
        proof=r['selected_identity_evidence']
        entries.append({**r,'numeric_sha256_wavelength_flux':original['numeric_sha256_wavelength_flux'],
            'source_url':original['source_url'],'observation_id':{k:proof['direct_fits_header'][k] for k in ['PLATEID','MJD','FIBERID','RUN2D']},
            'unit_status':'verified_native_pixel_identity',
            'astrophysical_association_status':'separate_positional_review_required',
            'flux_quality_status':'assessed_separately_in_current_screen',
            'old_core_registry_remains_unchanged':True})
    result={'schema_version':'2026-10-19-additive-1','base_registry_path':str(basepath.relative_to(ROOT)),
        'base_registry_sha256':digest(basepath),'evidence_path':str(evidencepath.relative_to(ROOT)),
        'evidence_sha256':digest(evidencepath),'records':entries,
        'scope':'Only previously unresolved MWDD SDSS SHA keys with exactly one accepted spectral-density convention. A wavelength-independent original normalization remains unconstrained.',
        'integration_policy':'Opt-in only through research/unit_resolution_followup/overlay.py; historical core evidence lookup and all frozen outputs remain unchanged.'}
    (OUT/'overlay_registry.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


class UnitOverlay:
    def __init__(self,root=ROOT):
        self.root=Path(root);self.path=self.root/'research/unit_resolution_followup/overlay_registry.json'
        self.payload=json.loads(self.path.read_text())
        assert digest(self.root/self.payload['base_registry_path'])==self.payload['base_registry_sha256']
        assert digest(self.root/self.payload['evidence_path'])==self.payload['evidence_sha256']
        base=json.loads((self.root/self.payload['base_registry_path']).read_text())
        previous={r['mwdd_sha256']:r for r in base['records']}
        self.by_sha={}
        for r in self.payload['records']:
            key=r['mwdd_sha256']
            if key in self.by_sha:raise ValueError('Duplicate overlay SHA')
            if previous[key]['convention']!='unresolved' or r['convention'] not in ['fnu','flambda']:
                raise ValueError('Overlay may only resolve previously unresolved raw SHA keys')
            proof=r['selected_identity_evidence']
            if proof['convention']!=r['convention'] or proof['mwdd_sha256']!=key:
                raise ValueError('Inconsistent overlay proof')
            self.by_sha[key]=r

    def as_flux_lambda(self,w,f,ivar,record):
        entry=self.by_sha.get(record.get('sha256'))
        if entry is None:return base_as_flux_lambda(w,f,ivar,record)
        host=urlsplit(record.get('source_url','')).hostname
        if record.get('kind')!='SDSS' or host not in ['www.montrealwhitedwarfdatabase.org','montrealwhitedwarfdatabase.org']:
            raise UnverifiedFluxConvention('Overlay key does not match the proved MWDD SDSS source type')
        if record.get('source_url')!=entry['source_url']:
            raise UnverifiedFluxConvention('Overlay source URL differs from the exact proved source')
        w=np.asarray(w,float);f=np.asarray(f,float);iv=None if ivar is None else np.asarray(ivar,float)
        actual=hashlib.sha256(np.column_stack([w,f]).astype('<f8').tobytes()).hexdigest()
        expected=entry['numeric_sha256_wavelength_flux']
        if record.get('numeric_sha256_wavelength_flux')!=expected or actual!=expected:
            raise ValueError('Overlay spectral values differ from the exact SHA-pinned original')
        meta={'flux_units_validated':True,'flux_input_convention':entry['convention'],
            'flux_conversion_applied':entry['convention']=='fnu',
            'flux_unit_evidence':'Explicit 2026-10-19 additive native-pixel evidence: research/unit_resolution_followup/overlay_registry.json',
            'flux_evidence_direct_sha256':entry['direct_sha256'],
            'flux_evidence_external_reference_id':entry['external_reference_id'],
            'flux_unit_previous_status':'unresolved','flux_unit_overlay_version':self.payload['schema_version'],
            'flux_absolute_scale_note':'Spectral-density shape convention verified; a wavelength-independent archive scale is not an absolute-luminosity calibration.'}
        if entry['convention']=='fnu':
            if np.any(~np.isfinite(w)|(w<=0)):raise ValueError('Invalid wavelength for Fnu conversion')
            factor=C_ANGSTROM_PER_SECOND/w**2
            f=f*factor
            if iv is not None:iv=iv/factor**2
        return f,iv,meta


if __name__=='__main__':
    value=create();print('Additive evidence records',len(value['records']))
