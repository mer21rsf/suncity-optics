'use strict';
(()=>{
 const q=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let photos=[],index=0,timer=null,seconds=5,playing=!matchMedia('(prefers-reduced-motion: reduce)').matches,hover=false,focused=false;
 function stop(){clearInterval(timer);timer=null;}
 function start(){stop();if(playing&&!hover&&!focused&&!document.hidden&&photos.length>1)timer=setInterval(()=>show(index+1),seconds*1000);}
 function show(next){index=(next+photos.length)%photos.length;document.querySelectorAll('.customer-slide').forEach((s,i)=>s.hidden=i!==index);q('#photo-counter').textContent=(index+1)+' / '+photos.length;document.querySelectorAll('.photo-dot').forEach((d,i)=>{d.classList.toggle('selected',i===index);d.setAttribute('aria-pressed',String(i===index));});q('#photo-play').textContent=playing?'Pause slideshow':'Play slideshow';}
 function manual(next){playing=false;stop();show(next);}
 q('#photo-prev').onclick=()=>manual(index-1);q('#photo-next').onclick=()=>manual(index+1);q('#photo-play').onclick=()=>{playing=!playing;if(playing){hover=false;focused=false;}show(index);start();};
 q('#customer-moments').addEventListener('mouseenter',()=>{hover=true;stop();});q('#customer-moments').addEventListener('mouseleave',()=>{hover=false;start();});
 q('#customer-moments').addEventListener('focusin',()=>{focused=true;stop();});q('#customer-moments').addEventListener('focusout',()=>{setTimeout(()=>{focused=q('#customer-moments').contains(document.activeElement);start();},0);});document.addEventListener('visibilitychange',start);
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');reduced.addEventListener?.('change',e=>{if(e.matches){playing=false;stop();if(photos.length)show(index);}});
 (async()=>{try{const response=await fetch('/suncityoptics/api/customer-photos');if(!response.ok)return;const j=await response.json();photos=j.photos||[];seconds=[4,5,7,10].includes(j.seconds)?j.seconds:5;if(!photos.length)return;
 q('#customer-slides').innerHTML=photos.map(p=>`<figure class="customer-slide" hidden><a href="${esc(p.image)}" target="_blank" rel="noopener" aria-label="Open larger customer photo"><img src="${esc(p.image)}" alt="${esc(p.alt)}" loading="lazy"></a>${p.title||p.caption?`<figcaption>${p.title?`<strong>${esc(p.title)}</strong>`:''}${p.caption?`<p>${esc(p.caption)}</p>`:''}</figcaption>`:''}</figure>`).join('');
 q('#photo-dots').innerHTML=photos.map((_,i)=>`<button type="button" class="photo-dot" aria-label="Show customer photo ${i+1}" aria-pressed="false" data-index="${i}"></button>`).join('');document.querySelectorAll('.photo-dot').forEach(b=>b.onclick=()=>manual(Number(b.dataset.index)));q('#customer-moments').hidden=false;q('#photo-prev').disabled=photos.length<2;q('#photo-next').disabled=photos.length<2;q('#photo-play').hidden=photos.length<2;show(0);start();
 }catch{/* Keep the section hidden rather than showing broken customer content. */}})();
})();
