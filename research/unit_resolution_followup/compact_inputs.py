#!/usr/bin/env python3
"""Lossless numerical evidence for every tested reference, without raw cache.

Full wavelength/flux vectors are preserved exactly as used by the identity
test. A shared dictionary compresses wavelengths without rounding. Native
float32 SDSS values are retained when their documented scaling reproduces the
float64 analysis vector bit for bit. Full originals remain URL/SHA pinned.
"""
from __future__ import annotations
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT))
import numpy as np
from astropy.io import fits
from fetch_and_identify import parse_original


def sha(b): return hashlib.sha256(b).hexdigest()
def array_sha(a): return sha(np.asarray(a).tobytes(order='C'))


def prepare():
    records = json.loads((OUT/'retrieval_all.json').read_text())['records']
    evidence = json.loads((OUT/'unit_evidence_all.json').read_text())
    quality_refs = {r['external_reference_id'] for r in evidence['records'] if r['convention'] != 'unresolved'}
    # Process only the deliberately bounded 3719-file retrieval; no directory
    # discovery can add an unselected or unhashed input.
    raw = {}; waves = []
    for r in records:
        assert r['status'] == 'verified'
        blob = (OUT/r['raw_path']).read_bytes(); assert sha(blob) == r['sha256']
        value = parse_original(blob,r)
        raw[r['key']] = value
        waves.append(value['wave'])
    dictionary = np.unique(np.concatenate(waves))
    assert np.all(np.isfinite(dictionary)), 'Nonfinite wavelength requires an explicit serialization policy'
    bundle = OUT/'compact'; bundle.mkdir(exist_ok=True)
    wavebuffer = io.BytesIO(); np.save(wavebuffer,dictionary,allow_pickle=False)
    (bundle/'wavelength_dictionary.npy.gz').write_bytes(gzip.compress(wavebuffer.getvalue(),mtime=0))
    dictionary_meta = {'file':'compact/wavelength_dictionary.npy.gz','sha256':sha((bundle/'wavelength_dictionary.npy.gz').read_bytes()),
        'dtype':str(dictionary.dtype),'values':len(dictionary),'array_sha256':array_sha(dictionary)}
    entries=[]; shards=[]; buffer=io.BytesIO(); archive=zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6)
    shard_number=0
    def finish():
        archive.close()
        name=f'identity_arrays_{shard_number:03d}.npz'
        payload=buffer.getvalue();(bundle/name).write_bytes(payload)
        shards.append({'file':'compact/'+name,'sha256':sha(payload),'bytes':len(payload)})
    for n,r in enumerate(records):
        value=raw[r['key']]; prefix=f'r{n:04d}'
        wi=np.searchsorted(dictionary,value['wave']).astype('<u4')
        assert dictionary[wi].astype('<f8').tobytes() == value['wave'].astype('<f8').tobytes()
        f=np.asarray(value['flux'],dtype='<f8'); stored=f; encoding='float64_analysis_flux'
        if r['format']=='sdss':
            proposed=np.asarray(f/1e-17,dtype='<f4')
            if (proposed.astype('<f8')*1e-17).tobytes() == f.tobytes():
                stored=proposed;encoding='native_float32_times_1e-17'
        fields={'wave_index':wi,'flux':stored}
        row={'key':r['key'],'format':r['format'],'source_url':r['source_url'],'raw_sha256':r['sha256'],
            'raw_bytes':r['bytes'],'raw_header':value['header'],'pixel_count':len(f),
            'wavelength_array_sha256':array_sha(value['wave'].astype('<f8')),
            'analysis_flux_array_sha256':array_sha(f),'flux_encoding':encoding,
            'columns':value.get('columns'),'sha_verified_before_extraction':True}
        if r['format']=='mwdd' and value['ivar'] is not None:
            fields['ivar']=np.asarray(value['ivar'],dtype='<f8')
            row['ivar_encoding']='float64_analysis_ivar'
        if r['key'] in quality_refs:
            with fits.open(OUT/r['raw_path'],memmap=False) as h:
                fields['ivar']=np.asarray(h[1].data['ivar'],dtype='<f4')
                fields['and_mask']=np.asarray(h[1].data['and_mask'],dtype='<u4')
                fields['or_mask']=np.asarray(h[1].data['or_mask'],dtype='<u4')
                row['ivar_encoding']='native_float32_divided_by_1e-34'
                row['hdu2_quality']={k:(h[2].data[k][0].item() if isinstance(h[2].data[k][0],np.generic) else h[2].data[k][0])
                    for k in ['CLASS','SUBCLASS','Z','ZWARNING','SN_MEDIAN_ALL','PLATEQUALITY','SPECOBJID'] if k in h[2].data.names}
        row['shard']=f'compact/identity_arrays_{shard_number:03d}.npz'
        row['arrays']={}
        for field,array in fields.items():
            member=prefix+'_'+field+'.npy'
            ab=io.BytesIO();np.save(ab,array,allow_pickle=False)
            archive.writestr(member,ab.getvalue())
            row['arrays'][field]={'member':member,'dtype':str(array.dtype),'sha256':array_sha(array)}
        entries.append(row)
        if buffer.tell()>2_900_000 and n+1<len(records):
            finish();shard_number+=1;buffer=io.BytesIO();archive=zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6)
        if (n+1)%500==0:print('compact',n+1,'/',len(records),flush=True)
    finish()
    manifest={'schema_version':'1.0','records':entries,'shards':shards,'wavelength_dictionary':dictionary_meta,
        'records_count':len(entries),'quality_reference_count':len(quality_refs),
        'total_compressed_array_bytes':sum(s['bytes'] for s in shards)+(bundle/'wavelength_dictionary.npy.gz').stat().st_size,
        'input_sha256':{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [OUT/'retrieval_all.json',OUT/'unit_evidence_all.json']},
        'code_sha256':sha(Path(__file__).read_bytes()),
        'limits':'These are exact, losslessly stored numerical extractions under verified raw SHA/URLs, not replacement original FITS/CSV byte streams. The raw SHA authenticates a redownload; the compact-array SHA authenticates the bundled numerical evidence. All tested flux and wavelength samples, including negative flux, remain. Native IVAR/AND/OR arrays are additionally kept for every newly accepted selected reference.'}
    (OUT/'compact_manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ['records','shards']},indent=2),flush=True)


class CompactInputs:
    def __init__(self,root=ROOT):
        self.root=Path(root);self.folder=self.root/'research/unit_resolution_followup'
        self.manifest=json.loads((self.folder/'compact_manifest.json').read_text())
        self.entries={r['key']:r for r in self.manifest['records']}
        d=self.manifest['wavelength_dictionary'];blob=(self.folder/d['file']).read_bytes()
        assert sha(blob)==d['sha256'];self.waves=np.load(io.BytesIO(gzip.decompress(blob)),allow_pickle=False)
        assert array_sha(self.waves)==d['array_sha256']
        self.shas={s['file']:s['sha256'] for s in self.manifest['shards']}
        self.cache={};self.loaded={}

    def load(self,key):
        if key in self.loaded:return self.loaded[key]
        row=self.entries[key];path=row['shard']
        if path not in self.cache:
            blob=(self.folder/path).read_bytes();assert sha(blob)==self.shas[path]
            with np.load(io.BytesIO(blob),allow_pickle=False) as data:
                self.cache[path]={k:np.asarray(data[k]) for k in data.files}
        table=self.cache[path];fields={}
        for field,meta in row['arrays'].items():
            arr=table[meta['member'][:-4]]
            assert str(arr.dtype)==meta['dtype'] and array_sha(arr)==meta['sha256']
            fields[field]=arr
        w=self.waves[fields['wave_index']];f=fields['flux'].astype('<f8')
        if row['flux_encoding']=='native_float32_times_1e-17':f=f*1e-17
        assert array_sha(w)==row['wavelength_array_sha256'] and array_sha(f)==row['analysis_flux_array_sha256']
        iv=fields.get('ivar')
        if iv is not None:iv=iv.astype('<f8')
        if row.get('ivar_encoding')=='native_float32_divided_by_1e-34':iv=iv/1e-34
        value={'wave':w,'flux':f,'ivar':iv,'header':row['raw_header'],'raw_sha256_verified':True,
            'compact_array_sha256_verified':True,'columns':row.get('columns')}
        for field in ['and_mask','or_mask']:
            if field in fields:value[field]=fields[field]
        self.loaded[key]=value
        return value


if __name__=='__main__':prepare()
