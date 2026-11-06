'use strict';
(()=>{
const q=s=>document.querySelector(s),form=q('#booking-form'),select=q('#service-select');
let month=null,data=null,selectedDay='',selectedTime='',sequence=0,loading=false;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const friendly=clock=>{const [h,m]=clock.split(':').map(Number);return `${h%12||12}:${String(m).padStart(2,'0')} ${h>=12?'PM':'AM'}`;};
const dayLabel=day=>new Intl.DateTimeFormat('en-CA',{timeZone:'UTC',weekday:'long',month:'long',day:'numeric',year:'numeric'}).format(new Date(day+'T12:00:00Z'));
function sync(){form.elements.day.value=selectedDay;form.elements.time.value=selectedTime;form.querySelector('button[type=submit]').disabled=loading||!selectedTime;q('#chosen-visit').textContent=selectedTime?`${dayLabel(selectedDay)} · ${friendly(selectedTime)} · ${data.minutes} minutes (Surrey time)`:'Select an available date and time.';}
function draw(){
 q('#calendar-panel').hidden=!data;
 if(!data){sync();return;}
 const [year,m]=data.month.split('-').map(Number);q('#calendar-month').textContent=new Intl.DateTimeFormat('en-CA',{timeZone:'UTC',month:'long',year:'numeric'}).format(new Date(Date.UTC(year,m-1,1)));
 q('#calendar-prev').disabled=data.month<=data.today.slice(0,7)||loading;q('#calendar-next').disabled=data.month>=data.max_date.slice(0,7)||loading;
 const blank=new Date(Date.UTC(year,m-1,1)).getUTCDay();
 q('#calendar-days').innerHTML='<span aria-hidden="true"></span>'.repeat(blank)+data.days.map(d=>`<button type="button" class="calendar-date ${d.state}${d.day===data.today?' today':''}${d.day===selectedDay?' selected':''}" data-day="${d.day}" ${d.state!=='available'?'disabled':''} aria-pressed="${d.day===selectedDay}" aria-label="${esc(dayLabel(d.day))}: ${d.state==='full'?'no openings':d.state}" title="${d.state==='full'?'No openings for this service':d.state}">${Number(d.day.slice(-2))}</button>`).join('');
 q('#calendar-days').querySelectorAll('button:not([disabled])').forEach(b=>b.onclick=()=>{selectedDay=b.dataset.day;selectedTime='';draw();});
 const day=data.days.find(d=>d.day===selectedDay);
 q('#time-title').textContent=day?`Available times · ${dayLabel(day.day)}`:'No openings this month for this service.';
 q('#calendar-hours').textContent=day?`Shop hours: ${friendly(day.opening)}–${friendly(day.closing)} · Appointment length: ${data.minutes} minutes.`:'Try another month or service.';
 q('#time-slots').innerHTML=day?day.slots.map(s=>`<button type="button" class="time-slot${s.time===selectedTime?' selected':''}" data-time="${s.time}" ${s.available?'':'disabled'} aria-pressed="${s.time===selectedTime}" aria-label="${friendly(s.time)} to ${friendly(s.end)}${s.available?'':': '+s.reason}">${friendly(s.time)}${s.available?'':`<small>${esc(s.reason)}</small>`}</button>`).join(''):'';
 q('#time-slots').querySelectorAll('button:not([disabled])').forEach(b=>b.onclick=()=>{selectedTime=b.dataset.time;draw();});sync();
}
async function refresh(preferDay=true){
 const request=++sequence;selectedTime='';loading=true;sync();q('#availability-status').textContent=select.value?'Checking available dates…':'Choose a service to see available dates and times.';
 if(!select.value){data=null;loading=false;draw();return;}
 try{
  const query=new URLSearchParams({service:select.value});if(month)query.set('month',month);
  const response=await fetch('/suncityoptics/api/availability?'+query);const result=await response.json();
  if(request!==sequence)return;if(!response.ok)throw Error(result.error||'Availability could not be loaded.');
  data=result;month=result.month;
  if(!preferDay||!result.days.some(d=>d.day===selectedDay&&d.state==='available'))selectedDay=result.days.find(d=>d.state==='available')?.day||'';
  q('#availability-status').textContent='Times are local to Surrey, BC. Grey times are unavailable.';
 }catch(error){if(request!==sequence)return;data=null;selectedDay='';q('#availability-status').textContent=error.message+' Please retry or call the shop.';}
 finally{if(request===sequence){loading=false;draw();}}
}
function navigate(amount){if(!month)return;const [y,m]=month.split('-').map(Number);const date=new Date(Date.UTC(y,m-1+amount,1));month=date.toISOString().slice(0,7);selectedDay='';refresh(false);}
q('#calendar-prev').onclick=()=>navigate(-1);q('#calendar-next').onclick=()=>navigate(1);q('#availability-refresh').onclick=()=>refresh();
select.addEventListener('change',()=>{q('#booking-result').textContent='';refresh();});
window.SunCityBooking={init:()=>refresh(),refresh:()=>refresh(),updateSubmit:sync,getSelection:()=>({day:selectedDay,time:selectedTime}),afterSuccess:()=>{selectedDay='';selectedTime='';data=null;refresh(false);}};
sync();
})();
