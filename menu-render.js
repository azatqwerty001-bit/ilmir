// Общие данные: публичный сайт и админка используют одну структуру меню.
(async () => {
  try {
    const response = await fetch('menu-data.json', {cache: 'no-cache'});
    if (!response.ok) throw new Error('Menu unavailable');
    let data = await response.json();
    if(new URLSearchParams(location.search).get('preview')==='1'){
      try{const saved=localStorage.getItem('cafe-menu-draft:'+new URL('.',location.href).pathname);if(saved)data=JSON.parse(saved);}catch{}
      const notice=document.createElement('div');notice.className='preview-notice';notice.textContent='Предпросмотр вашего черновика. Публичный сайт не изменён. ';
      const back=document.createElement('a');back.href='admin/';back.textContent='Вернуться к редактору';notice.append(back);document.body.prepend(notice);
    }
    const month = Number(new Intl.DateTimeFormat('en', {timeZone:'Europe/Moscow',month:'numeric'}).format(new Date()));
    const season = data.season === 'auto' ? (month >= 5 && month <= 9 ? 'summer' : 'winter') : data.season;
    const visible = data.items.filter(i => i.visible && (i.category !== 'seasonal' || i.season === 'all' || i.season === season));
    const fullMenu = !!document.querySelector('#menu-status');
    const grid = document.querySelector('.menu-grid');
    const el = (tag, text, cls) => { const node = document.createElement(tag); if (text) node.textContent = text; if (cls) node.className = cls; return node; };
    const card = i => {
      const article = el('article', '', 'menu-card'); article.dataset.category = i.category; article.id = i.id;
      const art = el('div','','item-art'); const img = el('img');
      img.src = i.image; img.alt = `${i.name}: пример подачи`; img.loading='lazy'; img.width=1000; img.height=680;
      art.append(img,el('small',i.label)); const copy=el('div','','item-copy'); const heading=el('div');
      heading.append(el('h3',i.name),el('span',`${i.price} ₽`,'price'));
      copy.append(heading,el('p',i.description),el('span',i.portion,'portion'));
      if(i.badge) copy.append(el('span',i.badge,'diet-tag'));
      const details=el('details','','ingredients');details.append(el('summary','Состав и аллергены'),el('p',`Состав: ${i.description}`),el('p',`Аллергены: ${i.allergens}`));
      copy.append(details);article.append(art,copy);return article;
    };
    if(grid) grid.replaceChildren(...(fullMenu ? visible : visible.filter(i=>i.category!=='seasonal').slice(0,3)).map(card));
    const seasonal=visible.filter(i=>i.category==='seasonal');
    document.querySelectorAll('.season-banner,.home-season').forEach(b=>{
      b.hidden=seasonal.length===0;
      const title=b.querySelector('h2'); if(title)title.textContent=data.seasonTitle;
      const desc=b.querySelector('p:not(.eyebrow)');if(desc)desc.textContent=data.seasonDescription;
      const eyebrow=b.querySelector('.eyebrow');if(eyebrow)eyebrow.textContent=season==='summer'?'ЛЕТНЕЕ ПРЕДЛОЖЕНИЕ':'ОСЕНЬ / ЗИМА';
      const link=b.querySelector('a[href^="#"]');if(link&&seasonal[0])link.href='#'+seasonal[0].id;
    });
    document.querySelectorAll('[data-filter]').forEach(button=>button.disabled=button.dataset.filter!=='all'&&!visible.some(i=>i.category===button.dataset.filter));
    if(fullMenu) document.querySelector('[data-filter="all"]').click();
  } catch (error) { console.warn('Используется сохранённая HTML-версия меню.', error.message); }
})();
