from django.core.management.base import BaseCommand,CommandError
from django.conf import settings
from cafe.telegram_bot import load_token,run_bot,TelegramError,explain_error
from cafe.views import menu_data
class Command(BaseCommand):
    help='Запуск Telegram-бота кофейни с общим меню из Django.'
    def handle(self,*args,**options):
        try:run_bot(load_token(settings.DATA_DIR),menu_data,settings.DATA_DIR,self.stdout.write)
        except KeyboardInterrupt:self.stdout.write('\nБот остановлен.')
        except (ValueError,TelegramError) as exc:
            if isinstance(exc,TelegramError):raise CommandError(explain_error(exc)) from None
            raise CommandError(str(exc)) from None
