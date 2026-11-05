"""Серверная корзина и подтверждение. Количество и сумма не принимаются на веру из callback."""
import secrets
from datetime import timedelta,datetime
from django.db import transaction
from django.utils import timezone
from .models import BotCart,BotEvent,Order,MenuItem,OrderNotice
from .telegram_bot import current_items,TelegramError

DEMO='Учебный заказ: настоящий кофе не готовится, оплата не требуется.'
def button(text,data):return {'text':text,'callback_data':data}
def reply(text,rows=None):return {'text':text,'reply_markup':{'inline_keyboard':rows or []}}
def available(provider):
    data={i['id']:i for i in current_items(provider())}
    return {str(i.pk):data[i.slug] for i in MenuItem.objects.all() if i.slug in data}
def summary(lines):return '\n'.join(f'{i["name"]} × {i["quantity"]} — {i["price"]*i["quantity"]} ₽' for i in lines)
def build_lines(cart,stock):
    if not cart.items:raise ValueError('Корзина пуста. Нажмите «Сделать заказ».')
    lines=[]
    for key,quantity in cart.items.items():
        if key not in stock:raise ValueError('Некоторые позиции больше недоступны. Удалите их из корзины и выберите другие.')
        item=stock[key];lines.append({'menu_id':key,'name':item['name'],'price':item['price'],'quantity':quantity})
    return lines

def catalog(stock,page=0):
    products=list(stock.items());last=max(0,(len(products)-1)//12);page=max(0,min(page,last))
    rows=[[button(f'{i["name"][:40]} · {i["price"]} ₽',f'add:{key}')] for key,i in products[page*12:(page+1)*12]]
    navigation=[]
    if page:navigation.append(button('← Назад',f'catalog:{page-1}'))
    if page<last:navigation.append(button('Далее →',f'catalog:{page+1}'))
    if navigation:rows.append(navigation)
    rows.append([button('🛒 Открыть корзину','cart')])
    return reply('Выберите позицию — нажатие добавляет 1 шт. (не более 10 одного вида). Состав и аллергены доступны в разделе «Меню».\n\n'+DEMO,rows)

def cart_view(cart,stock,prefix=''):
    rows=[];text=[];total=0
    for key,qty in cart.items.items():
        item=stock.get(key);name=item['name'] if item else 'Недоступная позиция'
        text.append(f'{name} × {qty}'+(f' — {item["price"]*qty} ₽' if item else ' — удалите из корзины'))
        if item:total+=item['price']*qty
        rows.append([button(f'− {name[:22]}',f'dec:{key}'),button('+',f'add:{key}'),button('Убрать',f'del:{key}')])
    if cart.items:rows.extend([[button('Оформить самовывоз','checkout')],[button('Очистить корзину','clear')]])
    rows.append([button('Добавить ещё','catalog')])
    return reply(prefix+'\n'.join(text)+(f'\n\nИтого: {total} ₽' if text else 'Корзина пуста.')+'\n\n'+DEMO,rows)

def review_view(cart,stock,pickup):
    lines=build_lines(cart,stock);total=sum(i['price']*i['quantity'] for i in lines)
    token=secrets.token_hex(16)
    cart.review={'token':token,'lines':lines,'total':total,'pickup':pickup,'created':timezone.now().isoformat()};cart.save()
    return reply('Проверьте заказ:\n\n'+summary(lines)+f'\n\nИтого: {total} ₽\nСамовывоз: {pickup}\n\n'+DEMO,[[button('Подтвердить учебный заказ','confirm:'+token)],[button('Вернуться в корзину','cart')]])

@transaction.atomic
def order_reply(update,provider,bot_key):
    event,created=BotEvent.objects.get_or_create(bot_key=bot_key,update_id=update['update_id'])
    if not created:return event.reply
    callback=update.get('callback_query');message=(callback or {}).get('message') if callback else update.get('message')
    if not message or message.get('chat',{}).get('type')!='private':return {}
    chat=message['chat']['id']
    if callback and callback.get('from',{}).get('id')!=chat:return {}
    cart,_=BotCart.objects.get_or_create(bot_key=bot_key,chat_id=chat)
    stock=available(provider)
    action=callback.get('data','') if callback else message.get('text','').strip()
    if action.startswith('/'):action=action.split('@',1)[0]
    if action in ('🛍 Сделать заказ','/order'):action='catalog'
    if action in ('🛒 Корзина','/cart'):action='cart'
    if action in ('📋 Мои заказы','/orders'):action='orders'
    if action in ('/cancel','Отменить оформление'):action='cancel_checkout'
    try:
        if action=='catalog':result=catalog(stock)
        elif action.startswith('catalog:'):
            try:page=int(action.split(':',1)[1])
            except ValueError:raise ValueError('Откройте каталог заново.')
            result=catalog(stock,page)
        elif action=='cart':result=cart_view(cart,stock)
        elif action=='orders':
            orders=Order.objects.filter(bot_key=bot_key,chat_id=chat)[:5]
            result=reply('\n\n'.join(f'№{o.pk} · {o.get_status_display()} · {o.total} ₽\nСамовывоз: {o.pickup}' for o in orders) or 'У вас пока нет заказов.')
        elif action.startswith(('add:','dec:','del:')):
            operation,key=action.split(':',1)
            if operation=='add':
                if key not in stock:raise ValueError('Эта позиция больше недоступна.')
                if cart.items.get(key,0)>=10 or sum(cart.items.values())>=50:raise ValueError('Лимит: 10 шт. одного вида и 50 шт. в корзине.')
                cart.items[key]=cart.items.get(key,0)+1
            elif key in cart.items:
                quantity=0 if operation=='del' else cart.items[key]-1
                if quantity:cart.items[key]=quantity
                else:del cart.items[key]
            cart.review={};cart.save();result=cart_view(cart,stock,'Корзина обновлена.\n\n')
        elif action=='clear':cart.items={};cart.review={};cart.save();result=cart_view(cart,stock)
        elif action=='cancel_checkout':cart.review={};cart.save();result=cart_view(cart,stock,'Оформление отменено, корзина сохранена.\n\n')
        elif action=='checkout':
            build_lines(cart,stock)
            now=timezone.localtime()
            result=reply('Когда заберёте учебный заказ? Время московское.\n\n'+DEMO,[[button('Как можно скорее','pickup:asap')],[button((now+timedelta(minutes=30)).strftime('%H:%M')+' (через 30 мин.)','pickup:30'),button((now+timedelta(minutes=60)).strftime('%H:%M')+' (через час)','pickup:60')],[button('Назад','cart')]])
        elif action.startswith('pickup:'):
            value=action.split(':',1)[1]
            if value not in ('asap','30','60'):raise ValueError('Выберите время кнопками.')
            pickup='Как можно скорее' if value=='asap' else (timezone.localtime()+timedelta(minutes=int(value))).strftime('%d.%m.%Y %H:%M МСК')
            result=review_view(cart,stock,pickup)
        elif action.startswith('confirm:'):
            token=action.split(':',1)[1]
            old=Order.objects.filter(confirmation=token,bot_key=bot_key,chat_id=chat).first()
            if old:result=reply(f'Заказ №{old.pk} уже отправлен. Статус: {old.get_status_display()}.\n\n'+DEMO)
            else:
                review=cart.review
                if not review or review.get('token')!=token:raise ValueError('Подтверждение устарело. Откройте корзину и оформите заказ заново.')
                if timezone.now()-datetime.fromisoformat(review['created'])>timedelta(minutes=15):raise ValueError('Прошло больше 15 минут. Проверьте заказ заново.')
                lines=build_lines(cart,stock)
                if lines!=review['lines']:cart.review={};cart.save();raise ValueError('Меню или цены изменились. Откройте корзину и подтвердите новую сумму.')
                order=Order.objects.create(bot_key=bot_key,chat_id=chat,confirmation=token,lines=lines,total=sum(i['price']*i['quantity'] for i in lines),pickup=review['pickup'])
                cart.items={};cart.review={};cart.save()
                result=reply(f'Учебный заказ №{order.pk} отправлен сотруднику.\n\n'+summary(lines)+f'\n\nИтого: {order.total} ₽\nСамовывоз: {order.pickup}\nСтатус: Новый\n\n'+DEMO,[[button('Мои заказы','orders')]])
        else:result=reply('Кнопка устарела. Откройте корзину заново.',[[button('Корзина','cart')]])
    except ValueError as error:result=reply(str(error),[[button('Открыть корзину','cart')]])
    event.reply=result;event.save(update_fields=['reply']);return result

def deliver_notices(api,bot_key):
    now=timezone.now()
    notices=OrderNotice.objects.filter(order__bot_key=bot_key,sent_at__isnull=True,permanent_failure=False).select_related('order').order_by('pk')[:10]
    for notice in notices:
        if notice.retry_at and notice.retry_at>now:continue
        if OrderNotice.objects.filter(order=notice.order,pk__lt=notice.pk,sent_at__isnull=True,permanent_failure=False).exists():continue
        order=notice.order;label=dict(Order._meta.get_field('status').choices)[notice.status]
        try:api.call('sendMessage',{'chat_id':order.chat_id,'text':f'Учебный заказ №{order.pk}: {label}.\nСамовывоз: {order.pickup}\n\n'+DEMO})
        except TelegramError as error:
            if error.code in (401,404,409):raise
            notice.attempts+=1;notice.error='Telegram '+str(error.code) if error.code else 'Сетевая ошибка'
            notice.permanent_failure=error.code in (400,403)
            notice.retry_at=now+timedelta(seconds=max(error.retry_after,min(300,5*2**min(notice.attempts,6))))
            notice.save();break
        else:notice.attempts+=1;notice.sent_at=timezone.now();notice.error='';notice.save()
