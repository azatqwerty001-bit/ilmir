"""Telegram long polling, стандартная библиотека; секреты не попадают в журнал."""
import hashlib,json,os,re,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from datetime import datetime
from zoneinfo import ZoneInfo

KEYBOARD={'keyboard':[[{'text':'☕ Меню'},{'text':'🍂 Сезонное'}],[{'text':'📍 Контакты'},{'text':'ℹ️ Помощь'}]],'resize_keyboard':True,'is_persistent':True}
class TelegramError(Exception):
    def __init__(self,code=0,retry_after=5):self.code=code;self.retry_after=min(max(retry_after,1),120);super().__init__(f'Telegram API error {code}')
class TelegramAPI:
    def __init__(self,token):
        if not re.fullmatch(r'\d{5,20}:[A-Za-z0-9_-]{20,}',token):raise ValueError('Токен имеет неверный формат. Скопируйте его целиком из BotFather.')
        self.token=token
    def call(self,method,payload=None):
        request=Request('https://api.telegram.org/bot'+self.token+'/'+method,data=json.dumps(payload or {}).encode(),headers={'Content-Type':'application/json'})
        try:
            with urlopen(request,timeout=45) as response:data=json.load(response)
        except HTTPError as exc:
            try:data=json.loads(exc.read())
            except (ValueError,OSError):data={}
            raise TelegramError(exc.code,data.get('parameters',{}).get('retry_after',5)) from None
        except (URLError,TimeoutError,OSError,ValueError):raise TelegramError() from None
        if not data.get('ok'):raise TelegramError(data.get('error_code',0),data.get('parameters',{}).get('retry_after',5))
        return data['result']

def load_token(state_dir):
    token=os.environ.get('TELEGRAM_BOT_TOKEN','').strip()
    if not token:
        file=Path(state_dir)/'telegram-token.txt'
        if not file.is_file():raise ValueError('Токен не настроен. Запустите start-bot-windows.bat для первого подключения.')
        token=file.read_text().strip()
    return token

def current_items(data,now=None):
    season=data['season']
    if season=='auto':
        month=(now or datetime.now(ZoneInfo('Europe/Moscow'))).month
        season='summer' if 5<=month<=9 else 'winter'
    return [i for i in data['items'] if i['visible'] and (i['category']!='seasonal' or i['season'] in ('all',season))]

def chunks(text,limit=3500):
    while len(text)>limit:
        cut=text.rfind('\n',0,limit)
        if cut<limit//2:cut=limit
        yield text[:cut]
        text=text[cut:].lstrip('\n')
    if text:yield text

def response_for(text,data):
    command=text.strip().split('@',1)[0] if text.strip().startswith('/') else text.strip()
    if command.split(' ',1)[0]=='/start':
        return 'Добро пожаловать в «Тёплый угол»!\nВыберите меню, сезонные предложения или контакты кнопками ниже.\n\nЭто учебная кофейня: адрес, рецептуры и цены вымышлены. Онлайн-заказы пока не принимаются.'
    if command in ('/menu','☕ Меню','Меню','/seasonal','🍂 Сезонное','Сезонное'):
        seasonal=command in ('/seasonal','🍂 Сезонное','Сезонное')
        items=current_items(data)
        if seasonal:items=[i for i in items if i['category']=='seasonal']
        if not items:return 'Сезонных предложений пока нет.' if seasonal else 'Меню обновляется. Загляните чуть позже.'
        title=(data['seasonTitle']+'\n'+data['seasonDescription']) if seasonal else 'Меню «Тёплого угла»'
        lines=[title,'']
        for i in items:
            lines.extend([f'{i["name"]} — {i["price"]} ₽ · {i["portion"]}',f'Состав: {i["description"]}',f'Аллергены: {i["allergens"]}'])
            if i['badge']:lines.append(i['badge'])
            lines.append('')
        lines.append('Учебное меню. Реальный состав и следовые аллергены нужно уточнять перед заказом.')
        return '\n'.join(lines)
    if command in ('/contacts','📍 Контакты','Контакты'):
        return 'Тёплый угол\nКазань, ул. Уютная, 12\n\nПн–Пт: 08:00–21:00\nСб–Вс: 09:00–22:00\n\nWi-Fi · кофе с собой · рады питомцам\n\nАдрес вымышленный. Телефон, соцсеть и реальный маршрут пока не подключены.'
    return 'Доступные команды:\n/start — начало\n/menu — меню и цены\n/seasonal — активное сезонное предложение\n/contacts — адрес и расписание\n/help — помощь\n\nМожно просто нажимать кнопки под сообщением.'

def handle_update(api,update,provider):
    message=update.get('message',{})
    # Учебный бот отвечает в личных сообщениях; группы и редактирования пропускает.
    if message.get('chat',{}).get('type')!='private':return
    chat_id=message['chat']['id'];text=message.get('text','')
    answer=response_for(text,provider())
    for part in chunks(answer):api.call('sendMessage',{'chat_id':chat_id,'text':part,'reply_markup':KEYBOARD})

def run_bot(token,provider,state_dir,log=print):
    api=TelegramAPI(token)
    me=api.call('getMe')
    # Не удаляем webhook автоматически: это мог бы быть другой работающий сервер.
    if api.call('getWebhookInfo').get('url'):raise ValueError('У бота уже настроен webhook. Нужен отдельный токен для учебного запуска либо осознанное отключение старого сервера.')
    identity=hashlib.sha256(token.encode()).hexdigest()[:16]
    cursor=Path(state_dir)/('telegram-offset-'+identity+'.json')
    try:offset=int(json.loads(cursor.read_text())['offset'])
    except (OSError,ValueError,KeyError,TypeError):offset=0
    log('Бот подключён: @'+me['username']+'. Откройте его в Telegram и нажмите «Запустить».')
    log('Не закрывайте это окно. Для остановки нажмите Ctrl+C.')
    while True:
        try:
            updates=api.call('getUpdates',{'offset':offset,'timeout':25,'allowed_updates':['message']})
            for update in updates:
                try:handle_update(api,update,provider)
                except TelegramError as exc:
                    if exc.code not in (400,403):raise
                    # Если получатель заблокировал бота, не застреваем на его обновлении.
                offset=update['update_id']+1
                temp=cursor.with_suffix('.tmp');temp.write_text(json.dumps({'offset':offset}));temp.replace(cursor)
        except TelegramError as exc:
            if exc.code in (401,404):raise ValueError('Telegram отклонил токен. Проверьте его в BotFather; при отзыве токена настройте новый.') from None
            if exc.code==409:raise ValueError('Этот бот уже запущен в другом окне или на другом сервере. Оставьте только один запуск.') from None
            log('Нет связи с Telegram или временный лимит. Повторяем подключение…')
            time.sleep(exc.retry_after)
