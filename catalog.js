'use strict';
(()=>{
 const q=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let offset=0,term='',loading=false,models=[],sequence=0;
 async function load(reset=false){if(loading&&!reset)return;const request=++sequence;loading=true;q('#more-models').disabled=true;q('#catalog-status').textContent='Loading eyeglass models…';if(reset){offset=0;models=[];q('#catalog-grid').innerHTML='';}
  try{const query=new URLSearchParams({offset:String(offset),q:term});const response=await fetch('/suncityoptics/api/products?'+query);const j=await response.json();if(request!==sequence)return;if(!response.ok)throw Error();models.push(...j.products);offset+=j.products.length;
   for(const product of j.products){const card=document.createElement('article');card.className='model-card';card.innerHTML=`<div class="model-photo"><img src="${esc(product.image)}" alt="${esc(product.name)}" loading="lazy"><span class="model-code">${esc(product.code)}</span></div><div class="model-copy"><h3>${esc(product.name)}</h3><p>${esc(product.description)}</p><button class="button outline model-inquiry" type="button" data-id="${product.id}">Ask about price & availability ↗</button></div>`;q('#catalog-grid').append(card);card.querySelector('button').onclick=()=>window.SunCityInquiry(product.code,product.name);}
   q('#catalog-empty').hidden=models.length>0;q('#catalog-empty').textContent=term?'No models match this search. Ask our team about a design you have in mind.':'Our team is preparing the model gallery. Ask us about the frames you’re looking for.';q('#more-models').hidden=!j.has_more;q('#catalog-status').textContent=models.length?models.length+' models shown · Ask us using the code on each card.':'';
  }catch{if(request===sequence)q('#catalog-status').textContent='The model gallery is temporarily unavailable. Please try again later.';}
  finally{if(request===sequence){loading=false;q('#more-models').disabled=false;}}
 }
 q('#more-models').onclick=()=>load();q('#catalog-search-form').onsubmit=e=>{e.preventDefault();term=q('#catalog-search').value.trim();load(true);};load(true);
})();
