from pathlib import Path
import urllib.request,json,hashlib,datetime
ROOT=Path(__file__).resolve().parent/'reference';ROOT.mkdir(exist_ok=True)
urls=['https://files.cie.co.at/Publications-datasets/CIE_xyz_1931_2deg.csv','https://files.cie.co.at/Publications-datasets/CIE_xyz_1931_2deg.csv_metadata.json']
log=[]
for url in urls:
    path=ROOT/url.rsplit('/',1)[1]
    if not path.exists():
        with urllib.request.urlopen(url,timeout=30) as r:path.write_bytes(r.read())
    b=path.read_bytes();log.append({'url':url,'path':str(path),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'md5':hashlib.md5(b).hexdigest(),'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
(ROOT/'reference_downloads.json').write_text(json.dumps(log,indent=2))
print(json.dumps(log,indent=2))
