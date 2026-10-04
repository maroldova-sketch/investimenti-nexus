"""Validate the bundle, copied release, real public HTTP responses and PDF QR."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote,urljoin
import argparse,hashlib,io,json,re,sys,urllib.request,urllib.error

ROOT=Path(__file__).resolve().parent.parent
TARGET='https://viladum.investimenti.cz/'
OLD_HOST='viladum-v-zahradach-brozura.jancaka.chatgpt.site'
ADDRESS='Osvoboditelů 497, Louny'

def require(condition,message):
    if not condition: raise ValueError(message)

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

class References(HTMLParser):
    def __init__(self): super().__init__(); self.refs=[]; self.ids=set()
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs: self.ids.add(attrs['id'])
        for name in ['src','href','data-full']:
            if attrs.get(name): self.refs.append(attrs[name])

def validate_html(folder):
    page=(folder/'index.html').read_text()
    require(ADDRESS in page,'Project address missing from HTML')
    require(OLD_HOST not in page,'Old hostname in HTML')
    require(f'content="{TARGET}"' in page,'Final OG URL missing')
    refs=References(); refs.feed(page)
    for ref in refs.refs:
        if ref.startswith('#'):
            require(ref[1:] in refs.ids,f'Missing HTML anchor {ref}')
            continue
        parsed=urlparse(ref)
        if parsed.scheme or parsed.netloc: continue
        path=folder/unquote(parsed.path).lstrip('/')
        require(path.is_file(),f'Missing referenced file {ref}')
    css=(folder/'style.css').read_text()
    for ref in re.findall(r'url\([\'\"]?([^\)\'\"]+)',css):
        if urlparse(ref).scheme or ref.startswith('data:'): continue
        require((folder/unquote(urlparse(ref).path)).is_file(),f'Missing CSS asset {ref}')
    require((folder/'brozura.pdf').read_bytes().startswith(b'%PDF-'),'Brochure is not a PDF')
    data=json.loads((folder/'projektova-data.json').read_text())
    require(data['adresa_projektu']==ADDRESS,'Wrong address in project JSON')
    require(len(data['byty'])==6,'Apartment count changed')
    require([u['celkem_dle_projektu_m2'] for u in data['byty']]==['82,25','89,35','92,15','94,45','116,45','99,65'],'Apartment areas changed')
    return {'html_local_links':'PASS','address':'PASS','apartments':'6; unchanged areas'}

def verify_bundle():
    manifest=json.loads((ROOT/'manifest.json').read_text())
    require(manifest['target']==TARGET,'Wrong manifest target')
    for name,sha in manifest['files'].items():
        rel=Path(name)
        require(not rel.is_absolute() and '..' not in rel.parts,'Unsafe manifest path')
        path=ROOT/rel
        require(path.is_file() and not path.is_symlink(),f'Missing regular file {name}')
        require(digest(path)==sha,f'Hash mismatch for {name}')
    actual={p.relative_to(ROOT/'public').as_posix() for p in (ROOT/'public').rglob('*') if p.is_file()}
    expected={name[7:] for name in manifest['files'] if name.startswith('public/')}
    require(actual==expected,'Unexpected or missing files in public/')
    require(not any(p.is_symlink() for p in (ROOT/'public').rglob('*')),'Symlink in public/')
    result={'bundle_hashes':f'PASS; {len(manifest["files"])} files'}
    result.update(validate_html(ROOT/'public'))
    return result

def verify_release(folder):
    manifest=json.loads((ROOT/'manifest.json').read_text())
    expected={name[7:]:sha for name,sha in manifest['files'].items() if name.startswith('public/')}
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    require(actual==set(expected),'Copied release files do not match public/')
    for name,sha in expected.items(): require(digest(folder/name)==sha,f'Release hash mismatch {name}')
    return {'release_hashes':f'PASS; {len(expected)} files'}

def verify_pdf(blob):
    import fitz
    from PIL import Image
    import zxingcpp
    pdf=fitz.open(stream=blob,filetype='pdf')
    require(len(pdf)==27,f'Expected 27 PDF pages, found {len(pdf)}')
    text='\n'.join(page.get_text() for page in pdf)
    require(ADDRESS in text,'Project address missing from PDF')
    uris=[item['uri'] for page in pdf for item in page.get_links() if item.get('uri')]
    require(not any(OLD_HOST in uri for uri in uris),'Old hostname in PDF links')
    require(any(uri.rstrip('/')==TARGET.rstrip('/') for uri in uris),'Final web link missing from PDF')
    pix=pdf[-1].get_pixmap(matrix=fitz.Matrix(3,3),alpha=False)
    im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
    values=[barcode.text for barcode in zxingcpp.read_barcodes(im)]
    require(any(v.rstrip('/')==TARGET.rstrip('/') for v in values),f'QR does not decode to final URL: {values}')
    require(all(v.rstrip('/')==TARGET.rstrip('/') for v in values),'Unexpected additional QR destination')
    return {'pdf_pages':len(pdf),'pdf_bytes':len(blob),'pdf_links':'PASS','pdf_address':'PASS','qr':'PASS','qr_decoded':values,'pdf_sha256':hashlib.sha256(blob).hexdigest()}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl): return None

def fetch(url):
    opener=urllib.request.build_opener(NoRedirect)
    req=urllib.request.Request(url,headers={'User-Agent':'ViladumDeploymentCheck/1.0','Cache-Control':'no-cache'})
    with opener.open(req,timeout=30) as response:
        require(response.status==200,f'{url} HTTP {response.status}')
        return response.read(),response.headers

def verify_live(pdf_check):
    page,headers=fetch(TARGET)
    require('text/html' in headers.get('Content-Type','').lower(),'Root is not HTML')
    html=page.decode('utf-8')
    require('Viladům' in html and ADDRESS in html,'Root is not the expected project page')
    require(OLD_HOST not in html,'Old hostname on public page')
    require('cloudflareaccess.com' not in html.lower(),'Access/login response instead of project')
    require('brozura.pdf' in html,'Brochure download missing from public HTML')
    blob,pdf_headers=fetch(urljoin(TARGET,'brozura.pdf'))
    require('application/pdf' in pdf_headers.get('Content-Type','').lower(),'Brochure has wrong MIME type')
    require(blob.startswith(b'%PDF-'),'PDF URL returned another document')
    expected=json.loads((ROOT/'manifest.json').read_text())['files']['public/brozura.pdf']
    require(hashlib.sha256(blob).hexdigest()==expected,'Live PDF differs from the supplied bundle')
    parser=References(); parser.feed(html)
    require(all('byt-'+letter in parser.ids for letter in 'abcdef'),'Apartment sections missing from public HTML')
    html_matches=hashlib.sha256(page).hexdigest()==digest(ROOT/'public/index.html')
    local={ref for ref in parser.refs if ref.startswith('assets/') or ref in {'style.css','brochure.js','podklady-projektu.zip'}}
    for ref in sorted(local):
        data,_=fetch(urljoin(TARGET,ref))
        require(hashlib.sha256(data).hexdigest()==digest(ROOT/'public'/ref),f'Live asset differs: {ref}')
    report={'public_root':'HTTP 200; expected project content','html_bytes_match_bundle':html_matches,'public_pdf':'HTTP 200; application/pdf; exact PDF','public_assets':f'PASS; {len(local)} files','login':'not required'}
    if not html_matches: report['html_delivery_note']='HTML delivery differs bytewise; CDN email obfuscation or injection may be present. Required project content was checked.'
    require(pdf_check,'Live completion requires --pdf; use ./verify.sh --live')
    report.update(verify_pdf(blob))
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bundle',action='store_true')
    parser.add_argument('--release',type=Path)
    parser.add_argument('--pdf',action='store_true')
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    report=verify_bundle()
    if args.release: report.update(verify_release(args.release))
    if args.pdf and not args.live: report.update(verify_pdf((ROOT/'public/brozura.pdf').read_bytes()))
    if args.live: report.update(verify_live(args.pdf))
    print(json.dumps({'result':'PASS','target':TARGET,**report},ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'result':'FAIL','error':str(exc)},ensure_ascii=False),file=sys.stderr)
        sys.exit(1)
