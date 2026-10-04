"""Refresh package hashes after an intentional local rebuild."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parent.parent
SKIP={'manifest.json','verification-report.json','LOCAL-VALIDATION.json'}
files={}
for path in sorted(ROOT.rglob('*')):
    rel=path.relative_to(ROOT)
    if any(p in {'.venv','__pycache__','.git','.DS_Store'} for p in rel.parts): continue
    if rel.as_posix() in SKIP or not path.is_file(): continue
    if path.is_symlink(): raise SystemExit(f'Symlinks are not allowed in the bundle: {rel}')
    files[rel.as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
(ROOT/'manifest.json').write_text(json.dumps({'schema':1,'target':'https://viladum.investimenti.cz/','project_address':'Osvoboditelů 497, Louny','files':files},ensure_ascii=False,indent=2)+'\n')
print(f'Manifest refreshed: {len(files)} files')
