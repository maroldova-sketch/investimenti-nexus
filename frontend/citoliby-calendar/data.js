const YEAR=2027, LAT=50.33139, LON=13.81194, TZ='Europe/Prague';
const CATEGORIES=['Divadlo','Koncert','Svatba','Gastro','Event'];
const PLACES=['Zahrada','Sala Terrena','Nádvoří'];
const MONTHS=['leden','únor','březen','duben','květen','červen','červenec','srpen','září','říjen','listopad','prosinec'];
const WEEK=['Po','Út','St','Čt','Pá','So','Ne'];
const SEED=[{"id": "e1", "start": "2027-01-15", "end": "2027-01-16", "title": "Zabijačka I", "category": "Gastro", "place": "Nádvoří", "startTime": "11:00", "endTime": "20:00", "status": "Návrh", "notes": ""}, {"id": "e2", "start": "2027-02-06", "end": "2027-02-07", "title": "Masopust + zabijačka II", "category": "Event", "place": "Nádvoří", "startTime": "11:00", "endTime": "20:00", "status": "Návrh", "notes": ""}, {"id": "e3", "start": "2027-03-19", "end": "2027-03-20", "title": "Postní / Josefský víkend", "category": "Gastro", "place": "Sala Terrena", "startTime": "17:00", "endTime": "22:00", "status": "Návrh", "notes": ""}, {"id": "e4", "start": "2027-03-27", "end": "2027-03-28", "title": "Velikonoce", "category": "Event", "place": "Nádvoří", "startTime": "10:00", "endTime": "18:00", "status": "Návrh", "notes": ""}, {"id": "e5", "start": "2027-04-30", "end": "2027-04-30", "title": "Čarodějnice", "category": "Event", "place": "Zahrada", "startTime": "16:00", "endTime": "23:00", "status": "Návrh", "notes": ""}, {"id": "e6", "start": "2027-05-07", "end": "2027-05-09", "title": "Chřestové slavnosti", "category": "Gastro", "place": "Nádvoří", "startTime": "11:00", "endTime": "20:00", "status": "Návrh", "notes": ""}, {"id": "e7", "start": "2027-05-21", "end": "2027-05-23", "title": "Jahodový víkend", "category": "Gastro", "place": "Zahrada", "startTime": "11:00", "endTime": "21:00", "status": "Návrh", "notes": ""}, {"id": "e8", "start": "2027-06-11", "end": "2027-06-13", "title": "Růže + hudba", "category": "Koncert", "place": "Zahrada", "startTime": "17:00", "endTime": "23:00", "status": "Návrh", "notes": ""}, {"id": "e9", "start": "2027-06-21", "end": "2027-06-21", "title": "Slavnosti slunovratu", "category": "Event", "place": "Zahrada", "startTime": "16:00", "endTime": "23:59", "status": "Návrh", "notes": "Signature večer světla, ohně a hudby."}, {"id": "e10", "start": "2027-06-23", "end": "2027-06-24", "title": "Svatojánské slavnosti", "category": "Event", "place": "Zahrada", "startTime": "17:00", "endTime": "23:59", "status": "Návrh", "notes": "23. 6. Svatojánská noc, 24. 6. pokračování."}, {"id": "e11", "start": "2027-06-28", "end": "2027-06-28", "title": "Souboj klavírů", "category": "Koncert", "place": "Nádvoří", "startTime": "19:30", "endTime": "22:30", "status": "Potvrzeno", "notes": ""}, {"id": "e12", "start": "2027-07-02", "end": "2027-07-04", "title": "Rosé & meloun", "category": "Gastro", "place": "Zahrada", "startTime": "11:00", "endTime": "22:00", "status": "Návrh", "notes": ""}, {"id": "e13", "start": "2027-07-09", "end": "2027-07-11", "title": "Francouzský brunch", "category": "Gastro", "place": "Zahrada", "startTime": "10:00", "endTime": "18:00", "status": "Návrh", "notes": ""}, {"id": "e14", "start": "2027-07-16", "end": "2027-07-18", "title": "Levandulový víkend", "category": "Gastro", "place": "Zahrada", "startTime": "11:00", "endTime": "21:00", "status": "Návrh", "notes": ""}, {"id": "e15", "start": "2027-07-24", "end": "2027-07-25", "title": "Svatojakubská pouť", "category": "Event", "place": "Nádvoří", "startTime": "10:00", "endTime": "22:00", "status": "Návrh", "notes": ""}, {"id": "e16", "start": "2027-08-20", "end": "2027-08-22", "title": "Chmel & pivo", "category": "Gastro", "place": "Nádvoří", "startTime": "11:00", "endTime": "23:00", "status": "Návrh", "notes": ""}, {"id": "e17", "start": "2027-08-28", "end": "2027-08-29", "title": "Dožínky / sklizeň", "category": "Event", "place": "Nádvoří", "startTime": "10:00", "endTime": "20:00", "status": "Návrh", "notes": ""}, {"id": "e18", "start": "2027-09-17", "end": "2027-09-19", "title": "Vinobraní", "category": "Gastro", "place": "Nádvoří", "startTime": "11:00", "endTime": "21:00", "status": "Návrh", "notes": ""}, {"id": "e19", "start": "2027-10-02", "end": "2027-10-03", "title": "Svatováclavské hody", "category": "Gastro", "place": "Nádvoří", "startTime": "11:00", "endTime": "20:00", "status": "Návrh", "notes": ""}, {"id": "e20", "start": "2027-10-08", "end": "2027-10-10", "title": "Husí slavnosti", "category": "Gastro", "place": "Sala Terrena", "startTime": "11:00", "endTime": "20:00", "status": "Návrh", "notes": ""}, {"id": "e21", "start": "2027-10-22", "end": "2027-10-24", "title": "Dýňový / podzimní sklizeň", "category": "Gastro", "place": "Nádvoří", "startTime": "10:00", "endTime": "19:00", "status": "Návrh", "notes": ""}, {"id": "e22", "start": "2027-11-05", "end": "2027-11-07", "title": "Zvěřinový víkend", "category": "Gastro", "place": "Sala Terrena", "startTime": "17:00", "endTime": "22:00", "status": "Návrh", "notes": ""}, {"id": "e23", "start": "2027-11-13", "end": "2027-11-14", "title": "Svatomartinská + zabijačka III", "category": "Gastro", "place": "Nádvoří", "startTime": "11:00", "endTime": "20:00", "status": "Návrh", "notes": ""}, {"id": "e24", "start": "2027-11-18", "end": "2027-11-18", "title": "Beaujolais", "category": "Gastro", "place": "Sala Terrena", "startTime": "18:00", "endTime": "23:00", "status": "Návrh", "notes": ""}, {"id": "e25", "start": "2027-11-27", "end": "2027-12-19", "title": "Advent I–IV", "category": "Event", "place": "Nádvoří", "startTime": "10:00", "endTime": "20:00", "status": "Návrh", "notes": "Rozsah je pracovní blok; jednotlivé adventní dny lze později rozdělit."}, {"id": "e26", "start": "2027-12-31", "end": "2027-12-31", "title": "Silvestrovský bál", "category": "Event", "place": "Sala Terrena", "startTime": "19:00", "endTime": "02:00", "status": "Návrh", "notes": ""}];

let month=0, hist={}, forecast={}, histSource='', events=loadEvents();

function loadEvents(){
  const x=localStorage.getItem('citoliby.events.v2');
  if(!x){localStorage.setItem('citoliby.events.v2',JSON.stringify(SEED));return structuredClone(SEED)}
  try{return JSON.parse(x)}catch(e){return structuredClone(SEED)}
}
function saveEvents(){localStorage.setItem('citoliby.events.v2',JSON.stringify(events))}
function iso(d){return d.toISOString().slice(0,10)}
function localISO(y,m,d){return `${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`}
function inRange(date,e){return date>=e.start && date<=e.end}
function uid(){return 'e'+Date.now().toString(36)+Math.random().toString(36).slice(2,7)}

function dayOfYear(y,m,d){return Math.floor((Date.UTC(y,m,d)-Date.UTC(y,0,0))/86400000)}
function solarTime(y,m,d,zenith,isRise){
 const N=dayOfYear(y,m,d), lngHour=LON/15;
 const t=N+((isRise?6:18)-lngHour)/24;
 const M=(0.9856*t)-3.289;
 let L=M+1.916*Math.sin(M*Math.PI/180)+0.020*Math.sin(2*M*Math.PI/180)+282.634; L=(L+360)%360;
 let RA=Math.atan(0.91764*Math.tan(L*Math.PI/180))*180/Math.PI; RA=(RA+360)%360;
 const Lq=Math.floor(L/90)*90, RAq=Math.floor(RA/90)*90; RA=(RA+(Lq-RAq))/15;
 const sinDec=.39782*Math.sin(L*Math.PI/180), cosDec=Math.cos(Math.asin(sinDec));
 const cosH=(Math.cos(zenith*Math.PI/180)-sinDec*Math.sin(LAT*Math.PI/180))/(cosDec*Math.cos(LAT*Math.PI/180));
 if(cosH>1||cosH<-1)return null;
 let H=isRise?360-Math.acos(cosH)*180/Math.PI:Math.acos(cosH)*180/Math.PI; H/=15;
 const T=H+RA-(.06571*t)-6.622;
 let UT=(T-lngHour)%24;if(UT<0)UT+=24;
 const dt=new Date(Date.UTC(y,m,d,Math.floor(UT),Math.round((UT%1)*60)));
 return new Intl.DateTimeFormat('cs-CZ',{timeZone:TZ,hour:'2-digit',minute:'2-digit',hour12:false}).format(dt);
}
function sunData(y,m,d){return {sunset:solarTime(y,m,d,90.833,false),dusk:solarTime(y,m,d,96,false)}}

function parseCSV(text){
 const first=text.split(/\r?\n/,1)[0], delim=(first.match(/;/g)||[]).length>(first.match(/,/g)||[]).length?';':',';
 const rows=[]; let row=[],cur='',q=false;
 for(let i=0;i<text.length;i++){const c=text[i],n=text[i+1];
   if(c=='"'){if(q&&n=='"'){cur+='"';i++}else q=!q}
   else if(c==delim&&!q){row.push(cur);cur=''}
   else if((c=='\n'||c=='\r')&&!q){if(c=='\r'&&n=='\n')i++;row.push(cur);if(row.some(x=>x.trim()))rows.push(row);row=[];cur=''}
   else cur+=c;
 } if(cur||row.length){row.push(cur);rows.push(row)}
 return rows;
}
function normalizeDate(s){
 s=(s||'').trim();
 let m=s.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/); if(m)return `${m[1]}-${m[2].padStart(2,'0')}-${m[3].padStart(2,'0')}`;
 m=s.match(/^(\d{1,2})[.](\d{1,2})[.](\d{4})/); if(m)return `${m[3]}-${m[2].padStart(2,'0')}-${m[1].padStart(2,'0')}`;
 return null;
}
function aggregateHistory(pairs){
 const bins={};
 for(const [date,val] of pairs){
   const y=+date.slice(0,4); if(y<1991||y>new Date().getFullYear()-1||!Number.isFinite(val)||val<0)continue;
   const md=date.slice(5); if(md==='02-29')continue;
   (bins[md]??=[]).push(val);
 }
 const out={};
 for(const [md,a] of Object.entries(bins)){
   out[md]={avg:a.reduce((s,x)=>s+x,0)/a.length, rain:a.filter(x=>x>=0.1).length/a.length*100, heavy:a.filter(x=>x>=5).length/a.length*100,n:a.length};
 }
 return out;
}
async function loadCHMI(){
 const url='https://opendata.chmi.cz/meteorology/climate/historical_csv/data/daily/precipitation/dly-0-203-0-11465-SRA.csv';
 const r=await fetch(url); if(!r.ok)throw new Error('CHMI '+r.status);
 const rows=parseCSV(await r.text()); if(rows.length<100)throw new Error('CHMI format');
 const header=rows[0].map(x=>x.trim().toLowerCase());
 let di=header.findIndex(x=>/date|datum|time|cas|čas/.test(x)), vi=header.findIndex(x=>/value|hodnota|sra|precip|úhrn|uhrn/.test(x));
 const pairs=[];
 for(let ri=di>=0?1:0;ri<rows.length;ri++){
   const row=rows[ri]; let date=di>=0?normalizeDate(row[di]):null;
   if(!date){for(const cell of row){date=normalizeDate(cell);if(date)break}}
   if(!date)continue;
   let val=vi>=0?Number(String(row[vi]).replace(',','.')):NaN;
   if(!Number.isFinite(val)){
     const dpos=row.findIndex(x=>normalizeDate(x));
     for(let j=dpos+1;j<row.length;j++){const n=Number(String(row[j]).replace(',','.'));if(Number.isFinite(n)&&n>=0&&n<1000){val=n;break}}
   }
   if(Number.isFinite(val))pairs.push([date,val]);
 }
 if(pairs.length<500)throw new Error('CHMI parsing');
 return aggregateHistory(pairs);
}
async function loadNASA(){
 const end=(new Date().getFullYear()-1)+'1231';
 const u=`https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR&community=AG&longitude=${LON}&latitude=${LAT}&start=19910101&end=${end}&format=JSON`;
 const r=await fetch(u); if(!r.ok)throw new Error('NASA '+r.status); const j=await r.json();
 const p=j?.properties?.parameter?.PRECTOTCORR||{}; const pairs=[];
 for(const [k,v] of Object.entries(p)){if(k.length===8){pairs.push([`${k.slice(0,4)}-${k.slice(4,6)}-${k.slice(6,8)}`,Number(v)])}}
 if(pairs.length<500)throw new Error('NASA data'); return aggregateHistory(pairs);
}
async function loadHistory(){
 const cacheKey='citoliby.hist.v3.'+(new Date().getFullYear()-1), cached=localStorage.getItem(cacheKey);
 if(cached){try{const c=JSON.parse(cached);hist=c.data;histSource=c.source;return}catch(e){}}
 try{hist=await loadCHMI();histSource='ČHMÚ Smolnice';}
 catch(e){console.warn(e);hist=await loadNASA();histSource='NASA POWER fallback';}
 localStorage.setItem(cacheKey,JSON.stringify({data:hist,source:histSource,at:Date.now()}));
}