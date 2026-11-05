from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import BotCart,Order,MenuItem,OrderNotice
from .orders import order_reply,deliver_notices
from .permissions import customer_group
from .views import menu_data
from .telegram_bot import TelegramError,handle_update

class OrdersTests(TestCase):
    @classmethod
    def setUpTestData(cls):call_command('import_menu',verbosity=0)
    def setUp(self):self.number=0;self.item=MenuItem.objects.get(slug='cappuccino')
    def action(self,action,chat=123,update_id=None):
        self.number+=1
        update={'update_id':update_id or self.number,'callback_query':{'id':str(self.number),'from':{'id':chat},'message':{'chat':{'id':chat,'type':'private'}},'data':action}}
        return order_reply(update,menu_data,'testbot')
    def checkout(self):
        self.action('add:'+str(self.item.pk));self.action('pickup:asap')
        return BotCart.objects.get(chat_id=123).review['token']
    def test_full_order_duplicate_confirmation_and_snapshot(self):
        self.action('add:'+str(self.item.pk),update_id=1)
        self.action('add:'+str(self.item.pk),update_id=1)
        self.assertEqual(BotCart.objects.get(chat_id=123).items[str(self.item.pk)],1)
        self.action('pickup:30');token=BotCart.objects.get(chat_id=123).review['token']
        result=self.action('confirm:'+token);self.assertIn('отправлен сотруднику',result['text'])
        order=Order.objects.get();self.assertEqual(order.total,240);self.assertIn('МСК',order.pickup)
        self.action('confirm:'+token);self.assertEqual(Order.objects.count(),1)
        self.assertEqual(BotCart.objects.get(chat_id=123).items,{})
        self.item.price=999;self.item.name='Новое название';self.item.save()
        order.refresh_from_db();self.assertEqual(order.total,240);self.assertEqual(order.lines[0]['name'],'Капучино')
    def test_price_availability_and_expiry_revalidation(self):
        token=self.checkout();self.item.price=250;self.item.save()
        self.assertIn('цены изменились',self.action('confirm:'+token)['text']);self.assertFalse(Order.objects.exists())
        self.action('pickup:asap');token=BotCart.objects.get(chat_id=123).review['token'];self.item.visible=False;self.item.save()
        self.assertIn('недоступны',self.action('confirm:'+token)['text']);self.assertFalse(Order.objects.exists())
        self.item.visible=True;self.item.save();self.action('pickup:asap')
        cart=BotCart.objects.get(chat_id=123);token=cart.review['token'];cart.review['created']=(timezone.now()-timedelta(minutes=16)).isoformat();cart.save()
        self.assertIn('15 минут',self.action('confirm:'+token)['text']);self.assertFalse(Order.objects.exists())
    def test_cart_limits_remove_clear_and_cancel(self):
        for _ in range(10):self.action('add:'+str(self.item.pk))
        self.assertIn('Лимит',self.action('add:'+str(self.item.pk))['text'])
        self.action('dec:'+str(self.item.pk));self.assertEqual(BotCart.objects.get(chat_id=123).items[str(self.item.pk)],9)
        self.action('pickup:asap');self.action('/cancel');self.assertEqual(BotCart.objects.get(chat_id=123).review,{})
        self.action('del:'+str(self.item.pk));self.assertEqual(BotCart.objects.get(chat_id=123).items,{})
        self.action('add:'+str(self.item.pk));self.action('clear');self.assertIn('пуста',self.action('checkout')['text'])
    def test_chat_isolation(self):
        token=self.checkout()
        self.assertIn('устарело',self.action('confirm:'+token,chat=456)['text']);self.assertFalse(Order.objects.exists())
        self.action('confirm:'+token)
        self.assertIn('пока нет',self.action('orders',chat=456)['text'])
        self.assertIn('№',self.action('orders')['text'])
    def test_admin_status_and_notifications(self):
        token=self.checkout();self.action('confirm:'+token);order=Order.objects.get()
        user=get_user_model().objects.create_user('staff',password='test-only-pass-56789',is_staff=True);user.groups.add(customer_group());self.client.force_login(user)
        self.assertEqual(self.client.get('/admin/cafe/order/').status_code,200)
        response=self.client.post(f'/admin/cafe/order/{order.pk}/change/',{'status':'accepted','_save':'Сохранить','notices-TOTAL_FORMS':'0','notices-INITIAL_FORMS':'0','notices-MIN_NUM_FORMS':'0','notices-MAX_NUM_FORMS':'0'})
        self.assertEqual(response.status_code,302)
        order.refresh_from_db();self.assertEqual(order.status,'accepted');self.assertEqual(order.notices.count(),1)
        class API:
            def __init__(self):self.sent=[]
            def call(self,m,p):self.sent.append(p);return {}
        api=API();deliver_notices(api,'testbot');self.assertIn('Принят',api.sent[0]['text']);self.assertIsNotNone(OrderNotice.objects.get().sent_at)
        deliver_notices(api,'testbot');self.assertEqual(len(api.sent),1)
        order.status='issued'
        with self.assertRaises(ValidationError):order.save()
        order.status='ready';order.save();order.status='issued';order.save()
        self.assertEqual(order.notices.count(),3)
        self.assertEqual(self.client.get('/admin/auth/user/').status_code,403)
        self.assertEqual(self.client.get('/admin/cafe/order/add/').status_code,403)
    def test_retry_permanent_failure_and_bot_identity(self):
        token=self.checkout();self.action('confirm:'+token);order=Order.objects.get();order.status='accepted';order.save()
        class FailAPI:
            def __init__(self,code):self.code=code
            def call(self,*args):raise TelegramError(self.code)
        deliver_notices(FailAPI(0),'other-bot');self.assertEqual(OrderNotice.objects.get().attempts,0)
        deliver_notices(FailAPI(0),'testbot');notice=OrderNotice.objects.get();self.assertIsNone(notice.sent_at);self.assertIsNotNone(notice.retry_at)
        notice.retry_at=timezone.now()-timedelta(seconds=1);notice.save()
        deliver_notices(FailAPI(403),'testbot');notice.refresh_from_db();self.assertTrue(notice.permanent_failure)
    def test_callback_transport_acknowledges_and_routes(self):
        class API:
            def __init__(self):self.calls=[]
            def call(self,m,p):self.calls.append((m,p));return {}
        api=API();handle_update(api,{'update_id':1,'callback_query':{'id':'callback','from':{'id':123},'message':{'chat':{'id':123,'type':'private'}},'data':'add:'+str(self.item.pk)}},menu_data,'testbot')
        self.assertEqual(api.calls[0][0],'answerCallbackQuery');self.assertEqual(api.calls[1][0],'sendMessage')
        self.assertEqual(BotCart.objects.get(chat_id=123).items[str(self.item.pk)],1)

    def test_status_queue_preserves_order_during_retry(self):
        token=self.checkout();self.action('confirm:'+token);order=Order.objects.get()
        order.status='accepted';order.save();order.status='ready';order.save()
        first=order.notices.first();first.retry_at=timezone.now()+timedelta(minutes=1);first.save()
        class API:
            def __init__(self):self.sent=[]
            def call(self,m,p):self.sent.append(p);return {}
        api=API();deliver_notices(api,'testbot');self.assertFalse(api.sent)
        first.retry_at=timezone.now()-timedelta(seconds=1);first.save();deliver_notices(api,'testbot')
        self.assertEqual(len(api.sent),2);self.assertIn('Принят',api.sent[0]['text']);self.assertIn('Готов',api.sent[1]['text'])
    def test_cancellation_and_stale_confirmation(self):
        token=self.checkout();self.action('add:'+str(self.item.pk))
        self.assertIn('устарело',self.action('confirm:'+token)['text'])
        self.action('pickup:asap');token=BotCart.objects.get(chat_id=123).review['token'];self.action('confirm:'+token)
        order=Order.objects.get();order.status='cancelled';order.save();self.assertEqual(order.notices.get().status,'cancelled')
        order.status='accepted'
        with self.assertRaises(ValidationError):order.save()
