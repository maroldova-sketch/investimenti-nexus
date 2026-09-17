function symbolCZ(s){
 if(!s)return 'forecast';
 if(s.includes('clearsky'))return 'jasno'; if(s.includes('fair'))return 'skoro jasno'; if(s.includes('partlycloudy'))return 'polojasno';
 if(s.includes('cloudy'))return 'oblačno'; if(s.includes('rain'))return 'déšť'; if(s.includes('snow'))return 'sníh'; if(s.includes('fog'))return 'mlha'; if(s.includes('thunder'))return 'bouřky'; return s.replaceAll('_',' ');
}
function render(){
 monthTitle.textContent=`${MONTHS[month]} ${YEAR}`;
 calendar.innerHTML=''; weekHeader.innerHTML=WEEK.map(x=>`<div class="weekhead">${x}</div>`).join('');
 const first=new Date(YEAR,month,1), last=new Date(YEAR,month+1,0), offset=(first.getDay()+6)%7;
 const start=new Date(YEAR,month,1-offset), count=Math.ceil((offset+last.getDate())/7)*7;
 const cf=categoryFilter.value,pf=placeFilter.value;
 let occupied=new Set(), visibleEvents=events.filter(e=>(!cf||e.category===cf)&&(!pf||e.place===pf));
 for(let i=0;i<count;i++){
   const d=new Date(start);d.setDate(start.getDate()+i); const same=d.getMonth()===month, key=localISO(d.getFullYear(),d.getMonth(),d.getDate());
   let ev=visibleEvents.filter(e=>inRange(key,e)); if(ev.length)occupied.add(key);
   const md=key.slice(5), h=hist[md], s=sunData(d.getFullYear(),d.getMonth(),d.getDate()), f=forecast[key];
   const today=localISO(new Date().getFullYear(),new Date().getMonth(),new Date().getDate());
   const card=document.createElement('article');card.className='day'+(same?'':' other')+(key===today?' today':'')+(ev.length?' has-event':'');
   card.innerHTML=`<div class=daytop><div><div class=daynum>${d.getDate()}</div><div class=dow>${WEEK[(d.getDay()+6)%7]}</div></div><button class=add title="Přidat akci">+</button></div>
   <div class=astronomy><b>Slunce</b><div class=data-row><span>Západ</span><span>${s.sunset||'—'}</span></div><div class=data-row><span>Stmívání do</span><span>${s.dusk||'—'}</span></div></div>
   <div class=history><b>Historické srážky ${h?`· n=${h.n}`:''}</b>${h?`<div class=data-row><span>Průměr / den</span><span>${h.avg.toFixed(1)} mm</span></div><div class=data-row><span>Déšť ≥0,1 mm</span><span>${Math.round(h.rain)} %</span></div><div class=data-row><span>Silný ≥5 mm</span><span>${Math.round(h.heavy)} %</span></div>`:`<div class=data-row><span>načítám</span><span>…</span></div>`}</div>
   ${f?`<div class="forecast live"><b>Forecast MET Norway</b><div class=data-row><span>${symbolCZ(f.symbol)}</span><span>${Number.isFinite(f.min)?Math.round(f.min):'—'}…${Number.isFinite(f.max)?Math.round(f.max):'—'} °C</span></div><div class=data-row><span>Srážky</span><span>${f.precip.toFixed(1)} mm</span></div></div>`:`<div class="forecast wait"><b>Forecast</b><div>Objeví se automaticky v dosahu modelu (~9 dní).</div></div>`}
   <div class=events>${ev.map(e=>`<button class="eventchip c-${e.category}" data-id="${e.id}">${e.startTime?e.startTime+' · ':''}${escapeHTML(e.title)}<small>${e.category} · ${e.place}<span class=status>${e.status}</span></small></button>`).join('')}</div>`;
   card.querySelector('.add').onclick=()=>openNew(key); card.querySelectorAll('.eventchip').forEach(b=>b.onclick=()=>openEdit(b.dataset.id));
   calendar.appendChild(card);
 }
 const monthStart=localISO(YEAR,month,1), monthEnd=localISO(YEAR,month,last.getDate());
 const monthEvents=visibleEvents.filter(e=>e.end>=monthStart&&e.start<=monthEnd);
 sumEvents.textContent=monthEvents.length;sumBooked.textContent=occupied.size;
 const mid=Math.min(15,last.getDate()), midSun=sunData(YEAR,month,mid);sumSunset.textContent=midSun.sunset;sumDusk.textContent=midSun.dusk;
 const probs=[];for(let d=1;d<=last.getDate();d++){const q=hist[localISO(YEAR,month,d).slice(5)];if(q)probs.push(q.rain)}sumRain.textContent=probs.length?Math.round(probs.reduce((a,b)=>a+b,0)/probs.length)+' %':'—';
}
function escapeHTML(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function openNew(date){
 eventId.value='';modalTitle.textContent='Nová akce';eventTitle.value='';startDate.value=endDate.value=date;category.value='Event';place.value='Nádvoří';startTime.value='';endTime.value='';status.value='Návrh';notes.value='';deleteBtn.classList.add('hidden');eventDialog.showModal();
}
function openEdit(id){
 const e=events.find(x=>x.id===id);if(!e)return;eventId.value=e.id;modalTitle.textContent='Upravit akci';eventTitle.value=e.title;startDate.value=e.start;endDate.value=e.end;category.value=e.category;place.value=e.place;startTime.value=e.startTime||'';endTime.value=e.endTime||'';status.value=e.status||'Návrh';notes.value=e.notes||'';deleteBtn.classList.remove('hidden');eventDialog.showModal();
}
eventForm.onsubmit=e=>{e.preventDefault();const item={id:eventId.value||uid(),title:eventTitle.value.trim(),start:startDate.value,end:endDate.value,category:category.value,place:place.value,startTime:startTime.value,endTime:endTime.value,status:status.value,notes:notes.value.trim()};if(item.end<item.start)item.end=item.start;const i=events.findIndex(x=>x.id===item.id);if(i>=0)events[i]=item;else events.push(item);saveEvents();eventDialog.close();render()}
deleteBtn.onclick=()=>{if(eventId.value&&confirm('Smazat tuto akci?')){events=events.filter(x=>x.id!==eventId.value);saveEvents();eventDialog.close();render()}}
cancelBtn.onclick=closeDialog.onclick=()=>eventDialog.close();newBtn.onclick=()=>openNew(localISO(YEAR,month,1));
prevBtn.onclick=()=>{month=(month+11)%12;render()};nextBtn.onclick=()=>{month=(month+1)%12;render()};categoryFilter.onchange=placeFilter.onchange=render;
exportBtn.onclick=()=>{const blob=new Blob([JSON.stringify({version:2,year:YEAR,events},null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='citoliby-kalendar-2027.json';a.click();URL.revokeObjectURL(a.href)}
importFile.onchange=async e=>{const f=e.target.files[0];if(!f)return;try{const j=JSON.parse(await f.text());const arr=Array.isArray(j)?j:j.events;if(!Array.isArray(arr))throw 0;events=arr;saveEvents();render();alert('Kalendář importován.')}catch(_){alert('Soubor není platný export kalendáře.')}e.target.value=''}
(async()=>{
 render();
 let msgs=[];
 try{await loadHistory();msgs.push(`historie: ${histSource}`)}catch(e){console.warn(e);msgs.push('historie: nepodařilo se načíst')}
 render();
 await loadForecast();msgs.push('forecast: MET Norway');
 weatherStatus.textContent=msgs.join(' · ');weatherStatus.style.background='#e9f0e9';weatherStatus.style.color='#315e43';
 render();
})();