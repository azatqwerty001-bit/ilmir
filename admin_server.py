"""Учебный сервер: python3 admin_server.py --init, затем python3 admin_server.py."""
import argparse, hashlib, hmac, json, os, secrets, time, threading, zipfile, io, re, html
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
STATE=Path(os.environ.get('CAFE_ADMIN_STATE', str(ROOT.parent/'.ilmir-admin')))
LOCK=threading.Lock(); SESSIONS={}
def validate(data):
 if not isinstance(data,dict) or data.get('version')!=1 or data.get('season') not in ('winter','summer','auto'):raise ValueError('Неверные настройки сезона')
 for key in ('seasonTitle','seasonDescription'):
  if not isinstance(data.get(key),str) or not 1<=len(data[key])<=500:raise ValueError('Заполните заголовок и описание сезона')
 items=data.get('items')
 if not isinstance(items,list) or not 1<=len(items)<=100:raise ValueError('В меню должно быть от 1 до 100 позиций')
 ids=set()
 for i in items:
  if not isinstance(i,dict):raise ValueError('Неверная позиция')
  if not isinstance(i.get('id'),str) or not re.fullmatch('[a-z][a-z0-9-]{0,60}',i['id']) or i['id'] in ids:raise ValueError('ID должен быть уникальным: латинские буквы, цифры и дефис')
  ids.add(i['id'])
  for k in ('name','portion','description','allergens','badge','label'):
   if not isinstance(i.get(k),str) or len(i[k])>1000 or (k in ('name','portion','description','allergens') and not i[k].strip()):raise ValueError('Заполните название, порцию, состав и аллергены')
  if type(i.get('price')) is not int or not 1<=i['price']<=100000:raise ValueError('Цена: целое число от 1 до 100000')
  if type(i.get('visible')) is not bool or i.get('category') not in ('coffee','food','seasonal') or i.get('season') not in ('all','summer','winter'):raise ValueError('Неверная категория или видимость')
  if not isinstance(i.get('image'),str) or not re.fullmatch(r'assets/[a-z0-9-]+\.webp',i['image']) or not (ROOT/i['image']).is_file():raise ValueError('Выберите существующую фотографию')
 return data
def read_data():return json.loads((STATE/'menu.json').read_text()) if (STATE/'menu.json').exists() else json.loads((ROOT/'menu-data.json').read_text())
def atomic(path,data):
 temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2));os.chmod(temp,0o600);temp.replace(path)
def export(data):
 # Экспорт включает HTML-резерв для браузеров без JavaScript.
 from datetime import datetime
 from zoneinfo import ZoneInfo
 season=data['season'];season=('summer' if 5<=datetime.now(ZoneInfo('Europe/Moscow')).month<=9 else 'winter') if season=='auto' else season
 items=[i for i in data['items'] if i['visible'] and (i['category']!='seasonal' or i['season'] in ('all',season))]
 def card(i):
  e=lambda k:html.escape(str(i[k]),quote=True)
  return f'<article class="menu-card" id="{e("id")}" data-category="{e("category")}"><div class="item-art"><img src="{e("image")}" alt="{e("name")}: пример подачи" loading="lazy" width="1000" height="680"><small>{e("label")}</small></div><div class="item-copy"><div><h3>{e("name")}</h3><span class="price">{e("price")} ₽</span></div><p>{e("description")}</p><span class="portion">{e("portion")}</span><span class="diet-tag">{e("badge")}</span><details class="ingredients"><summary>Состав и аллергены</summary><p>Состав: {e("description")}</p><p>Аллергены: {e("allergens")}</p></details></div></article>'
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  for name in ('index.html','menu.html','contacts.html','style.css','script.js','menu-render.js'):
   text=(ROOT/name).read_text()
   if name in ('index.html','menu.html'):
    cards=items if name=='menu.html' else [i for i in items if i['category']!='seasonal'][:3]
    # Контейнер заканчивается сразу после последней карточки.
    match=re.search(r'<div class="menu-grid">(?:\s*<article\b.*?</article>\s*)+</div>',text,re.S)
    if match:text=text[:match.start()]+'<div class="menu-grid">'+''.join(map(card,cards))+'</div>'+text[match.end():]
    text=re.sub(r'Показано позиций: \d+',f'Показано позиций: {len(items)}',text)
    seasonal=[i for i in items if i['category']=='seasonal']
    def banner(m):
     block=m.group();block=re.sub(r'<h2>.*?</h2>','<h2>'+html.escape(data['seasonTitle'])+'</h2>',block,flags=re.S)
     block=re.sub(r'(<p class="eyebrow">).*?(</p>)',lambda n:n[1]+('ЛЕТО' if season=='summer' else 'ОСЕНЬ / ЗИМА')+n[2],block,flags=re.S)
     block=re.sub(r'<p>(.*?)</p>','<p>'+html.escape(data['seasonDescription'])+'</p>',block,count=1,flags=re.S)
     if not seasonal:block=block.replace('class="season-banner"','hidden class="season-banner"').replace('class="container home-season"','hidden class="container home-season"')
     if seasonal:block=re.sub(r'href="#[^"]+"','href="#'+seasonal[0]['id']+'"',block)
     return block
    text=re.sub(r'<aside class="season-banner".*?</aside>|<section class="container home-season".*?</section>',banner,text,flags=re.S)
   z.writestr(name,text)
  z.writestr('menu-data.json',json.dumps(data,ensure_ascii=False,indent=2))
  for p in (ROOT/'assets').iterdir():
   if p.suffix=='.webp' or p.name=='favicon.svg':z.write(p,str(p.relative_to(ROOT)))
 return out.getvalue()
class Handler(BaseHTTPRequestHandler):
 def send(self,status,data,kind='application/json',cookie=None):
  if isinstance(data,dict):data=json.dumps(data,ensure_ascii=False).encode()
  elif isinstance(data,str):data=data.encode()
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY')
  if cookie:self.send_header('Set-Cookie',cookie)
  if kind=='application/zip':self.send_header('Content-Disposition','attachment; filename="teply-ugol-site.zip"')
  self.end_headers();self.wfile.write(data)
 def session(self):
  cookie=self.headers.get('Cookie','');token=next((p.strip()[len('cafe_session='):] for p in cookie.split(';') if p.strip().startswith('cafe_session=')),None)
  return token if token in SESSIONS and SESSIONS[token]>time.time() else None
 def host_ok(self):
  return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
 def origin_ok(self):
  origin=self.headers.get('Origin');return bool(origin and urlsplit(origin).netloc==self.headers.get('Host') and urlsplit(origin).scheme in ('http','https'))
 def do_GET(self):
  if not self.host_ok():return self.send(403,{'error':'Недопустимый адрес сервера'})
  path=urlsplit(self.path).path
  if path=='/api/session':return self.send(200,{'authenticated':bool(self.session())})
  if path=='/api/menu':
   if not self.session():return self.send(401,{'error':'Войдите в админку'})
   return self.send(200,read_data())
  if path=='/api/export':
   if not self.session():return self.send(401,{'error':'Войдите в админку'})
   return self.send(200,export(read_data()),'application/zip')
  if path=='/menu-data.json':return self.send(200,read_data())
  allowed={'/':'index.html','/index.html':'index.html','/menu.html':'menu.html','/contacts.html':'contacts.html','/style.css':'style.css','/script.js':'script.js','/menu-render.js':'menu-render.js','/admin/':'admin/index.html','/admin':'admin/index.html','/admin/admin.js':'admin/admin.js','/admin/admin.css':'admin/admin.css'}
  name=allowed.get(path)
  if path.startswith('/assets/') and re.fullmatch(r'/assets/[a-z0-9-]+\.(webp|svg)',path):name=path[1:]
  if not name or not (ROOT/name).is_file():return self.send(404,{'error':'Не найдено'})
  import mimetypes
  if name in ('index.html','menu.html'):
   with zipfile.ZipFile(io.BytesIO(export(read_data()))) as z:return self.send(200,z.read(name),'text/html; charset=utf-8')
  return self.send(200,(ROOT/name).read_bytes(),mimetypes.guess_type(name)[0] or 'application/octet-stream')
 def do_POST(self):
  if not self.host_ok() or not self.origin_ok():return self.send(403,{'error':'Запрос должен идти с этого сайта'})
  try:
   length=int(self.headers.get('Content-Length',0))
   if not 0<length<=200000:raise ValueError('Размер запроса превышен')
   body=json.loads(self.rfile.read(length))
   path=urlsplit(self.path).path
   if path=='/api/login':
    # Ограничение попыток на клиентский адрес.
    now=time.time();attempts=self.server.attempts.setdefault(self.client_address[0],[]);attempts[:]=[t for t in attempts if t>now-60]
    if len(attempts)>=10:return self.send(429,{'error':'Слишком много попыток. Подождите минуту.'})
    attempts.append(now);config=json.loads((STATE/'auth.json').read_text());password=body.get('password','')
    if not isinstance(password,str) or len(password)>1000:raise ValueError('Неверный пароль')
    digest=hashlib.scrypt(password.encode(),salt=bytes.fromhex(config['salt']),n=16384,r=8,p=1).hex()
    if not hmac.compare_digest(digest,config['hash']):return self.send(401,{'error':'Неверный пароль'})
    token=secrets.token_urlsafe(32);SESSIONS[token]=now+28800
    return self.send(200,{'ok':True},cookie=f'cafe_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')
   if not self.session():return self.send(401,{'error':'Сессия истекла. Войдите снова.'})
   if path=='/api/logout':
    SESSIONS.pop(self.session(),None);return self.send(200,{'ok':True},cookie='cafe_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
   if path=='/api/menu':
    data=validate(body)
    with LOCK:atomic(STATE/'menu.json',data)
    return self.send(200,{'ok':True})
   return self.send(404,{'error':'Не найдено'})
  except (ValueError,KeyError,TypeError) as e:return self.send(400,{'error':str(e)})
 def log_message(self,*args):pass
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--init',action='store_true');parser.add_argument('--port',type=int,default=8001);args=parser.parse_args()
 STATE.mkdir(mode=0o700,parents=True,exist_ok=True)
 if args.init:
  import getpass
  password=os.environ.get('CAFE_ADMIN_PASSWORD') or getpass.getpass('Новый пароль администратора (не меньше 12 символов): ')
  if len(password)<12:raise SystemExit('Нужно минимум 12 символов')
  salt=secrets.token_bytes(16);atomic(STATE/'auth.json',{'salt':salt.hex(),'hash':hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1).hex()});print('Пароль установлен. Запустите python3 admin_server.py');raise SystemExit()
 if not (STATE/'auth.json').exists():raise SystemExit('Сначала выполните python3 admin_server.py --init')
 server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.attempts={};print(f'Локальная админка: http://127.0.0.1:{args.port}/admin/');server.serve_forever()
