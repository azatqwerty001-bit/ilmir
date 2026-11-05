import io,json,tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from django.test import TestCase,SimpleTestCase
from django.core.management import call_command
from .models import MenuItem,SeasonSettings
from .views import menu_data
from .telegram_bot import TelegramAPI,TelegramError,current_items,response_for,handle_update,chunks,run_bot
class FakeAPI:
    def __init__(self):self.sent=[]
    def call(self,method,payload=None):
        self.sent.append((method,payload));return {}
class BotTests(TestCase):
    @classmethod
    def setUpTestData(cls):call_command('import_menu',verbosity=0)
    def test_commands_and_database_changes(self):
        self.assertIn('Добро пожаловать',response_for('/start something',menu_data()))
        self.assertIn('240 ₽',response_for('/menu',menu_data()))
        item=MenuItem.objects.get(slug='cappuccino');item.price=299;item.save()
        self.assertIn('299 ₽',response_for('☕ Меню',menu_data()))
        item.visible=False;item.save();self.assertNotIn('Капучино',response_for('/menu',menu_data()))
        self.assertIn('вымышленный',response_for('/contacts',menu_data()))
        self.assertIn('/help',response_for('unknown',menu_data()))
    def test_manual_and_auto_season(self):
        self.assertIn('Пряный латте',response_for('/seasonal',menu_data()))
        config=SeasonSettings.objects.get();config.season='summer';config.save()
        self.assertIn('пока нет',response_for('/seasonal',menu_data()))
        data=menu_data();data['season']='auto'
        self.assertTrue(any(i['category']=='seasonal' for i in current_items(data,datetime(2026,11,5))))
        self.assertFalse(any(i['category']=='seasonal' for i in current_items(data,datetime(2026,7,5))))
    def test_private_chat_only_and_plain_text(self):
        api=FakeAPI();handle_update(api,{'message':{'chat':{'id':1,'type':'group'},'text':'/start'}},menu_data);self.assertEqual(api.sent,[])
        handle_update(api,{'message':{'chat':{'id':2,'type':'private'},'text':'/menu'}},menu_data)
        self.assertTrue(api.sent)
        for method,payload in api.sent:
            self.assertEqual(method,'sendMessage');self.assertEqual(payload['chat_id'],2);self.assertLessEqual(len(payload['text']),3500);self.assertNotIn('parse_mode',payload)
        self.assertTrue(all(len(chunk)<=3500 for chunk in chunks('a'*20000)))
class TransportTests(SimpleTestCase):
    def test_errors_never_include_token(self):
        token='123456:'+'x'*30
        with patch('cafe.telegram_bot.urlopen',side_effect=URLError('secret URL '+token)):
            with self.assertRaises(TelegramError) as caught:TelegramAPI(token).call('getMe')
        self.assertNotIn(token,str(caught.exception))
    def test_polling_cursor_and_webhook_protection(self):
        class Poller:
            def __init__(self):self.sent=[];self.offsets=[]
            def call(self,method,payload=None):
                if method=='getMe':return {'username':'demo_cafe_bot'}
                if method=='getWebhookInfo':return {'url':''}
                if method=='getUpdates':
                    self.offsets.append(payload['offset'])
                    if len(self.offsets)>1:raise KeyboardInterrupt
                    return [{'update_id':10,'message':{'chat':{'id':2,'type':'private'},'text':'/start'}}]
                self.sent.append(payload);return {}
        with tempfile.TemporaryDirectory() as directory:
            first=Poller()
            with patch('cafe.telegram_bot.TelegramAPI',return_value=first):
                with self.assertRaises(KeyboardInterrupt):run_bot('test-token',lambda:{},directory,lambda text:None)
            saved=list(Path(directory).glob('telegram-offset-*.json'));self.assertEqual(json.loads(saved[0].read_text())['offset'],11)
            second=Poller()
            with patch('cafe.telegram_bot.TelegramAPI',return_value=second):
                with self.assertRaises(KeyboardInterrupt):run_bot('test-token',lambda:{},directory,lambda text:None)
            self.assertEqual(second.offsets[0],11)
            self.assertNotIn('test-token',saved[0].read_text())
        with patch('cafe.telegram_bot.TelegramAPI') as factory:
            factory.return_value.call.side_effect=[{'username':'demo'},{'url':'https://existing.example'}]
            with self.assertRaisesMessage(ValueError,'webhook'):run_bot('test-token',lambda:{},'/tmp',lambda text:None)

class DiagnosticTests(SimpleTestCase):
    def test_distinguishes_token_and_network_without_secret(self):
        import ssl,socket
        from .telegram_bot import explain_error
        self.assertIn('отклонил токен',explain_error(TelegramError(401)))
        self.assertIn('сертификата',explain_error(TelegramError(kind='tls')))
        self.assertIn('DNS',explain_error(TelegramError(kind='dns')))
        self.assertIn('пока не удалось проверить',explain_error(TelegramError()))
        token='123456:'+'x'*30
        for reason,kind in [(ssl.SSLError('secret '+token),'tls'),(socket.gaierror('secret '+token),'dns'),(TimeoutError(token),'timeout')]:
            with patch('cafe.telegram_bot.urlopen',side_effect=URLError(reason)):
                with self.assertRaises(TelegramError) as caught:TelegramAPI(token).call('getMe')
            self.assertEqual(caught.exception.kind,kind)
            self.assertNotIn(token,explain_error(caught.exception))
            self.assertNotIn(token,str(caught.exception))
