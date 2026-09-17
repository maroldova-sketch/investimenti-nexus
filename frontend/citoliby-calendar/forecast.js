function localDateKey(dateStr){return new Intl.DateTimeFormat('en-CA',{timeZone:TZ,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(dateStr))}
async function loadForecast(){
 try{
   const u=`https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=${LAT}&lon=${LON}`;
   const r=await fetch(u,{headers:{'Accept':'application/json'}}); if(!r.ok)throw new Error('MET '+r.status);
   const j=await r.json(), ts=j?.properties?.timeseries||[], agg={};
   for(let i=0;i<ts.length;i++){
     const item=ts[i], key=localDateKey(item.time), d=item.data?.instant?.details||{};
     agg[key]??={temps:[],precip:0,symbol:'',points:0};
     if(Number.isFinite(d.air_temperature))agg[key].temps.push(d.air_temperature);
     const dt=new Date(item.time), hour=dt.getUTCHours();
     const n1=item.data?.next_1_hours, n6=item.data?.next_6_hours;
     if(n1?.details && Number.isFinite(n1.details.precipitation_amount)){agg[key].precip+=n1.details.precipitation_amount}
     else if(n6?.details && hour%6===0 && Number.isFinite(n6.details.precipitation_amount)){agg[key].precip+=n6.details.precipitation_amount}
     const sym=n1?.summary?.symbol_code||n6?.summary?.symbol_code||item.data?.next_12_hours?.summary?.symbol_code;
     if(sym)agg[key].symbol=sym; agg[key].points++;
   }
   for(const [k,a] of Object.entries(agg)){forecast[k]={min:Math.min(...a.temps),max:Math.max(...a.temps),precip:a.precip,symbol:a.symbol}}
 }catch(e){console.warn('forecast',e)}
}