const $=id=>document.getElementById(id);
let data,dirty=false;
const status=(text,error=false)=>{$('status').textContent=text;$('status').classList.toggle('error',error);};
async function api(path,body){const response=await fetch('../api/'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),cache:'no-store'});const result=await response.json();if(!response.ok)throw Error(result.error||'Ошибка сервера');return result;}
const mark=()=>{dirty=true;status('Есть несохранённые изменения. Нажмите «Сохранить на сервере».');};
const photos=['cappuccino','latte','croissant','filter-coffee','toast','cake','seasonal-latte','seasonal-tea','coffee-detail'].map(name=>'assets/'+name+'.webp');
function renderItems(){
 const root=$('items');root.replaceChildren();
 data.items.forEach((item,index)=>{
  const section=document.createElement('article');section.className='admin-item';
  const h=document.createElement('h3');h.textContent=item.name||'Новая позиция';section.append(h);
  const fields=document.createElement('div');fields.className='item-fields';
  function field(key,title,type='text',options){
   const label=document.createElement('label');label.textContent=title;
   let input=document.createElement(options?'select':type==='textarea'?'textarea':'input');
   if(options)options.forEach(([value,text])=>{const option=document.createElement('option');option.value=value;option.textContent=text;input.append(option)});
   else if(type!=='textarea')input.type=type;
   input.id=`item-${index}-${key}`;if(type==='number'){input.min=1;input.max=100000;input.step=1;}
   if(type==='checkbox'){input.checked=item[key];label.className='check-label'}else input.value=item[key];
   input.addEventListener('input',()=>{item[key]=type==='checkbox'?input.checked:type==='number'?Number(input.value):input.value;if(key==='name')h.textContent=input.value||'Новая позиция';if(key==='image')image.src='../'+input.value;mark();});
   if(type==='textarea')label.className='full-field';label.append(input);fields.append(label);
  }
  field('name','Название');field('price','Цена, ₽','number');field('portion','Порция (например, 250 мл)');field('category','Категория','text',[['coffee','Кофе'],['food','Выпечка и завтраки'],['seasonal','Сезонное']]);field('season','Когда показывать сезонную позицию','text',[['winter','Осень / зима'],['summer','Лето'],['all','Любой сезон']]);field('image','Фото-пример','text',photos.map(p=>[p,p.split('/')[1]]));field('description','Состав','textarea');field('allergens','Аллергены');field('badge','Пометка (например, без молока)');field('label','Короткая надпись на фото');field('id','Уникальный ID (латиница и дефисы)');field('visible','Показывать на сайте','checkbox');
  section.append(fields);const actions=document.createElement('div');actions.className='item-actions';const image=document.createElement('img');image.className='item-image';image.src='../'+item.image;image.alt='Предпросмотр фотографии';
  const remove=document.createElement('button');remove.type='button';remove.textContent='Удалить позицию';remove.addEventListener('click',()=>{if(confirm(`Удалить «${item.name}»?`)){data.items.splice(index,1);mark();renderItems();}});actions.append(image,remove);section.append(actions);root.append(section);
 });
}
async function openEditor(){data=await api('menu');$('login-panel').hidden=true;$('editor').hidden=false;for(const k of ['season','seasonTitle','seasonDescription'])$(k).value=data[k];renderItems();dirty=false;status('Вы вошли. Меню загружено с сервера.');}
$('login-form').addEventListener('submit',async event=>{event.preventDefault();try{await api('login',{password:$('password').value});$('password').value='';await openEditor();}catch(e){status(e.message,true);}});
for(const k of ['season','seasonTitle','seasonDescription'])$(k).addEventListener('input',()=>{data[k]=$(k).value;mark();});
$('add').addEventListener('click',()=>{const id='item-'+Date.now();data.items.push({id,name:'Новая позиция',price:250,portion:'250 мл',category:'seasonal',season:'summer',description:'Укажите состав',allergens:'Укажите аллергены',badge:'',label:'НОВИНКА',image:photos[0],visible:false});mark();renderItems();$('items').lastElementChild.scrollIntoView({behavior:'smooth'});});
$('save').addEventListener('click',async()=>{$('save').disabled=true;try{await api('menu',data);dirty=false;status('Сохранено на учебном сервере. Обновите вкладку меню. Публичный GitHub Pages пока не изменён.');}catch(e){status(e.message,true)}finally{$('save').disabled=false;}});
$('export').addEventListener('click',async()=>{if(dirty){status('Сначала сохраните изменения на сервере, затем скачайте ZIP.',true);return;}try{const r=await fetch('../api/export');if(!r.ok)throw Error('Войдите снова для экспорта');const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download='teply-ugol-site.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status('ZIP скачан. Распакуйте и загрузите файлы в main вашего репозитория.');}catch(e){status(e.message,true)}});
$('logout').addEventListener('click',async()=>{if(dirty&&!confirm('Выйти без сохранения изменений?'))return;try{await api('logout',{});dirty=false;data=null;$('items').replaceChildren();$('editor').hidden=true;$('login-panel').hidden=false;status('Вы вышли.');}catch(e){status(e.message,true)}});
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
(async()=>{try{const session=await api('session');if(session.authenticated)await openEditor();else{$('login-panel').hidden=false;status('Введите пароль администратора.');}}catch{$('offline-panel').hidden=false;status('Админка открыта без своего сервера. Данные сайта не изменены.',true);}})();
