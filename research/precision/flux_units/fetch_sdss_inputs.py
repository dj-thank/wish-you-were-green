#!/usr/bin/env python3
"""Acquire the exact SDSS exports and FITS needed for a flux-unit audit."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from research.outlier_audit.audit import inputs
from download_frozen_spectra import acquire

def run():
    jobs=[(i,(o,r)) for i,(o,r) in enumerate(inputs()) if r['kind']=='SDSS']
    def one(task):
        i,item=task
        try:
            r=acquire(item)
            return {'row_index':i,'status':r['status'],'sha256':r['sha256'],'source_url':r['source_url']}
        except Exception as exc:return {'row_index':i,'status':'error','error':str(exc)}
    results=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n,r in enumerate(pool.map(one,jobs),1):
            results.append(r)
            if n%200==0:print(n,'/',len(jobs),'errors',sum(r['status']=='error' for r in results),flush=True)
    (Path(__file__).resolve().parent/'retrieval.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Complete',len(results),'errors',sum(r['status']=='error' for r in results),flush=True)

if __name__=='__main__':run()
