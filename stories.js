'use strict';
(()=>{
 const q=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let offset=0,loading=false;
 async function load(){if(loading)return;loading=true;q('#more-stories').disabled=true;
  try{const response=await fetch('/suncityoptics/api/stories?offset='+offset);const data=await response.json();if(!response.ok)throw Error();
   if(offset===0)q('#story-wall').innerHTML='';
   for(const story of data.stories){const card=document.createElement('article');card.className='story-note note-'+(story.id%4);card.innerHTML=`<span class="note-pin" aria-hidden="true"></span><p>${esc(story.note)}</p><footer><strong>${esc(story.name)}</strong><span>${esc(new Intl.DateTimeFormat('en-CA',{month:'short',day:'numeric',year:'numeric',timeZone:'America/Vancouver'}).format(new Date(story.created)))}</span></footer>`;q('#story-wall').append(card);}
   offset+=data.stories.length;q('#story-empty').hidden=offset>0;q('#more-stories').hidden=!data.has_more;
  }catch{q('#stories-status').textContent='Our note wall is temporarily unavailable. Please try again later.';}
  finally{loading=false;q('#more-stories').disabled=false;}
 }
 q('#more-stories').onclick=load;
 q('#story-note-input').oninput=e=>q('#story-count').textContent=e.target.value.length+'/600';
 q('#story-form').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button[type=submit]');button.disabled=true;const result=q('#story-result');
  try{const response=await fetch('/suncityoptics/api/story',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});const data=await response.json();if(!response.ok)throw Error(data.error||'Please try again.');result.textContent='Thank you! Your note is waiting for admin approval before it appears on the wall.';e.target.reset();q('#story-count').textContent='0/600';}
  catch(error){result.textContent=error.message;}finally{button.disabled=false;}
 };
 load();
})();
