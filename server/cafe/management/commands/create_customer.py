import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group,Permission
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand,CommandError
from django.core.exceptions import ValidationError
from django.db import transaction
class Command(BaseCommand):
    help='Создать аккаунт заказчика: меню и сезон, без управления пользователями.'
    @transaction.atomic
    def handle(self,*args,**options):
        username=input('Логин заказчика: ').strip()
        User=get_user_model()
        if not username or User.objects.filter(username=username).exists():raise CommandError('Выберите новый непустой логин')
        password=getpass.getpass('Пароль (минимум 12 символов): ')
        if password!=getpass.getpass('Повторите пароль: '):raise CommandError('Пароли не совпали')
        user=User(username=username,is_staff=True)
        try:validate_password(password,user)
        except ValidationError as e:raise CommandError('; '.join(e.messages))
        group,_=Group.objects.get_or_create(name='Заказчик кофейни')
        group.permissions.set(Permission.objects.filter(content_type__app_label='cafe').exclude(codename__in=['add_seasonsettings','delete_seasonsettings']))
        user.set_password(password);user.save();user.groups.add(group)
        self.stdout.write('Аккаунт создан. Заказчик может войти в /admin/.')
