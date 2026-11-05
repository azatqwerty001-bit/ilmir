// Экспорт выполняется в браузере, без передачи черновика сторонним сервисам.
window.exportCafeSite=async function(data){
 const zip=new JSZip();
 const month=Number(new Intl.DateTimeFormat('en',{timeZone:'Europe/Moscow',month:'numeric'}).format(new Date()));
 const season=data.season==='auto'?(month>=5&&month<=9?'summer':'winter'):data.season;
 const items=data.items.filter(i=>i.visible&&(i.category!=='seasonal'||i.season==='all'||i.season===season));
 const element=(doc,tag,text,cls)=>{const node=doc.createElement(tag);if(text)node.textContent=text;if(cls)node.className=cls;return node;};
 function card(doc,i){
  const make=(tag,text,cls)=>element(doc,tag,text,cls);const article=make('article','','menu-card');article.id=i.id;article.dataset.category=i.category;
  const art=make('div','','item-art');const img=make('img');img.src=i.image;img.alt=i.name+': пример подачи';img.loading='lazy';img.width=1000;img.height=680;art.append(img,make('small',i.label));
  const copy=make('div','','item-copy');const head=make('div');head.append(make('h3',i.name),make('span',i.price+' ₽','price'));copy.append(head,make('p',i.description),make('span',i.portion,'portion'));if(i.badge)copy.append(make('span',i.badge,'diet-tag'));
  const details=make('details','','ingredients');details.append(make('summary','Состав и аллергены'),make('p','Состав: '+i.description),make('p','Аллергены: '+i.allergens));copy.append(details);article.append(art,copy);return article;
 }
 const assets=new Set(['assets/favicon.svg','assets/coffee-shop.webp','assets/coffee-detail.webp','assets/cafe-interior.webp','assets/cafe-entrance.webp',...data.items.map(i=>i.image)]);
 for(const name of ['index.html','menu.html','contacts.html','style.css','script.js','menu-render.js']){
  const r=await fetch('../'+name,{cache:'no-cache'});if(!r.ok)throw Error('Не удалось скачать '+name);let text=await r.text();
  if(name.endsWith('.html')){
   const doc=new DOMParser().parseFromString(text,'text/html');const grid=doc.querySelector('.menu-grid');if(grid)grid.replaceChildren(...(name==='menu.html'?items:items.filter(i=>i.category!=='seasonal').slice(0,3)).map(i=>card(doc,i)));
   const live=doc.querySelector('#menu-status');if(live)live.textContent='Показано позиций: '+items.length;
   const seasonal=items.filter(i=>i.category==='seasonal');doc.querySelectorAll('.season-banner,.home-season').forEach(b=>{b.hidden=!seasonal.length;b.querySelector('h2').textContent=data.seasonTitle;b.querySelector('p:not(.eyebrow)').textContent=data.seasonDescription;b.querySelector('.eyebrow').textContent=season==='summer'?'ЛЕТНЕЕ ПРЕДЛОЖЕНИЕ':'ОСЕНЬ / ЗИМА';const link=b.querySelector('a[href^="#"]');if(link&&seasonal[0])link.href='#'+seasonal[0].id;});
   doc.querySelectorAll('img').forEach(i=>assets.add(i.getAttribute('src')));text='<!doctype html>\n'+doc.documentElement.outerHTML;
  }
  zip.file(name,text);
 }
 zip.file('menu-data.json',JSON.stringify(data,null,2));
 for(const name of assets){if(!/^assets\/[a-z0-9-]+\.(webp|svg)$/.test(name))throw Error('Недопустимый путь изображения');const r=await fetch('../'+name);if(!r.ok)throw Error('Не удалось скачать '+name);zip.file(name,await r.arrayBuffer());}
 const url=URL.createObjectURL(await zip.generateAsync({type:'blob'}));const link=document.createElement('a');link.href=url;link.download='teply-ugol-site.zip';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
