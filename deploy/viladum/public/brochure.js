const viewer=document.getElementById('viewer');
const viewerImage=document.getElementById('viewer-image');
const viewerCaption=document.getElementById('viewer-caption');
const viewerOriginal=document.getElementById('viewer-original');
document.addEventListener('click',event=>{
 const button=event.target.closest('[data-full]');if(!button)return;
 const img=button.querySelector('img');viewerImage.src=button.dataset.full;viewerImage.alt=img.alt;
 viewerCaption.textContent=img.alt;viewerOriginal.href=button.dataset.full;viewer.showModal();
});
document.getElementById('close-viewer').addEventListener('click',()=>viewer.close());
viewer.addEventListener('click',event=>{if(event.target===viewer)viewer.close()});
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{
 const filter=button.dataset.filter;
 document.querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
 let count=0;document.querySelectorAll('.unit-card').forEach(card=>{card.hidden=filter!=='all'&&card.dataset.floor!==filter;if(!card.hidden)count++;});
 document.getElementById('selection-count').textContent=count===6?'6 bytů v projektu':'3 byty v podlaží';
}));
const toggle=document.querySelector('.menu-toggle'),mobileMenu=document.getElementById('mobile-menu');
toggle.addEventListener('click',()=>{const open=toggle.getAttribute('aria-expanded')==='true';toggle.setAttribute('aria-expanded',String(!open));mobileMenu.hidden=open;});
mobileMenu.addEventListener('click',event=>{if(event.target.closest('a')){mobileMenu.hidden=true;toggle.setAttribute('aria-expanded','false');}});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!mobileMenu.hidden){mobileMenu.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.focus();}});
