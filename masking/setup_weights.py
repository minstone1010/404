"""Install verified model weights from local release assets or GitHub Releases."""
import argparse,hashlib,json,os,shutil,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--from-dir',type=Path,help='Folder containing the two release assets');parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    manifest=json.loads((ROOT/'weights_manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['files']:
        target=(ROOT/entry['path']).resolve()
        if not target.is_relative_to(ROOT.resolve()):raise ValueError('Invalid model destination')
        if target.is_file() and target.stat().st_size==entry['size'] and digest(target)==entry['sha256']:
            print('OK:',entry['path']);continue
        if args.check_only:raise SystemExit('Missing or mismatched weights: '+entry['path'])
        target.parent.mkdir(parents=True,exist_ok=True);part=target.with_suffix('.download')
        try:
            if args.from_dir:
                shutil.copyfile(args.from_dir/entry['asset'],part)
            else:
                url='https://github.com/minstone1010/404/releases/download/'+manifest['release_tag']+'/'+entry['asset']
                print('Downloading:',entry['asset'],flush=True)
                with urllib.request.urlopen(url,timeout=60) as response,part.open('wb') as stream:shutil.copyfileobj(response,stream,8*1024*1024)
            if part.stat().st_size!=entry['size'] or digest(part)!=entry['sha256']:raise ValueError('Weight checksum mismatch: '+entry['asset'])
            os.replace(part,target);print('Installed:',entry['path'])
        finally:
            if part.exists():part.unlink()
if __name__=='__main__':main()
