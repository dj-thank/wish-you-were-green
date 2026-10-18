"""Resolve spectrum flux conventions before interpreting colour.

An archive/instrument name is insufficient for MWDD SDSS exports: both F_nu
and F_lambda occur. Only raw-SHA-matched evidence can authorize their use.
The primitive colour integrator continues to require F_lambda as its input.
"""
from __future__ import annotations
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
import numpy as np

ROOT=Path(__file__).resolve().parent
EVIDENCE=ROOT/'research/precision/flux_convention_evidence.json'
C_ANGSTROM_PER_SECOND=2.99792458e18

class UnverifiedFluxConvention(ValueError):
    """The shape convention is unknown, so a physical colour is unavailable."""

@lru_cache(maxsize=1)
def evidence_registry():
    if not EVIDENCE.exists():return {}
    data=json.loads(EVIDENCE.read_text())
    result={}
    for item in data['records']:
        key=item['mwdd_sha256']
        if key in result and result[key]['convention']!=item['convention']:
            raise ValueError('Conflicting flux-convention evidence for '+key)
        result[key]=item
    return result

def resolve_flux_convention(record):
    kind=record.get('kind','');host=urlsplit(record.get('source_url','')).hostname
    common={'flux_units_validated':False,'flux_input_convention':'unresolved',
        'flux_conversion_applied':False,'flux_unit_evidence':'No verified spectral-density convention'}
    if kind=='SDSS' and host=='data.sdss.org':
        return {**common,'flux_units_validated':True,'flux_input_convention':'flambda',
            'flux_unit_evidence':'Official SDSS FITS F_lambda contract; flux_sdss * 1e-17, BUNIT 1E-17 erg/cm^2/s/Ang'}
    if kind=='SDSS' and host in ('www.montrealwhitedwarfdatabase.org','montrealwhitedwarfdatabase.org'):
        entry=evidence_registry().get(record.get('sha256'))
        if entry and entry['convention'] in ('fnu','flambda'):
            return {**common,'flux_units_validated':True,'flux_input_convention':entry['convention'],
                'flux_unit_evidence':'Raw SHA matched against official SDSS native pixels: research/precision/flux_convention_evidence.json',
                'flux_evidence_direct_sha256':entry.get('direct_sha256','')}
        return {**common,'flux_unit_evidence':'MWDD SDSS convention is mixed; no decisive official-native-pixel match for this raw SHA'}
    if kind=='Gaia_XP' and host in ('www.montrealwhitedwarfdatabase.org','montrealwhitedwarfdatabase.org'):
        return {**common,'flux_units_validated':True,'flux_input_convention':'flambda',
            'flux_unit_evidence':'Gaia XP calibrated flux per wavelength; native GaiaXPy coefficient reconstruction checked for 26 sources in research/precision/gaia_expanded'}
    if kind=='DESI' and host in ('www.montrealwhitedwarfdatabase.org','montrealwhitedwarfdatabase.org'):
        return {**common,'flux_units_validated':True,'flux_input_convention':'flambda',
            'flux_unit_evidence':'DESI DR1 calibrated F_lambda export contract; original exposure comparisons in research/literature. Constant scale does not affect colour.'}
    return common

def as_flux_lambda(wavelength_angstrom,flux,inverse_variance,record):
    """Return relative F_lambda plus transformed noise and evidence metadata.

For F_nu-shaped exports a wavelength-independent original scale may remain
unknown; absolute luminosity is not inferred here. The c/lambda^2 conversion
is essential even when a later photometric fit can absorb a smooth tilt.
"""
    meta=resolve_flux_convention(record)
    if not meta['flux_units_validated']:
        raise UnverifiedFluxConvention(meta['flux_unit_evidence'])
    w=np.asarray(wavelength_angstrom,float);f=np.asarray(flux,float)
    iv=None if inverse_variance is None else np.asarray(inverse_variance,float)
    if record.get('numeric_sha256_wavelength_flux'):
        actual=hashlib.sha256(np.column_stack([w,f]).astype('<f8').tobytes()).hexdigest()
        if actual!=record['numeric_sha256_wavelength_flux']:
            raise ValueError('Parsed spectral values do not match the unit-verified frozen raw input')
    if meta['flux_input_convention']=='fnu':
        if np.any(~np.isfinite(w)|(w<=0)):raise ValueError('Invalid wavelength in F_nu conversion')
        factor=C_ANGSTROM_PER_SECOND/w**2
        f=f*factor
        if iv is not None:iv=iv/factor**2
        meta['flux_conversion_applied']=True
        meta['flux_absolute_scale_note']='Shape verified; a wavelength-independent archive scale may remain. No absolute luminosity claim.'
    return f,iv,meta
