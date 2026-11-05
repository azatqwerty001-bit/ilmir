import json
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from cafe.models import MenuItem,SeasonSettings
class Command(BaseCommand):
    help='Первый импорт учебного меню. Существующие данные не перезаписываются.'
    @transaction.atomic
    def handle(self,*args,**options):
        if MenuItem.objects.exists():self.stdout.write('Меню уже существует — оставлено без изменений.');return
        data=json.loads((settings.PROJECT_DIR/'menu-data.json').read_text())
        SeasonSettings.objects.get_or_create(pk=1,defaults={'season':data['season'],'title':data['seasonTitle'],'description':data['seasonDescription']})
        for n,item in enumerate(data['items']):
            MenuItem.objects.create(slug=item['id'],name=item['name'],category=item['category'],price=item['price'],portion=item['portion'],description=item['description'],allergens=item['allergens'],badge=item['badge'],label=item['label'],default_image=item['image'],visible=item['visible'],season=item['season'],position=n)
        self.stdout.write('Учебное меню импортировано.')
