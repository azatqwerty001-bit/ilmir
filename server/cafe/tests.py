import io,tempfile
from pathlib import Path
from django.test import TestCase,Client,override_settings
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission,Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from PIL import Image
from .models import MenuItem,SeasonSettings
from .views import rendered_pages

class CafeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('import_menu',verbosity=0)
        cls.customer=get_user_model().objects.create_user('customer',password='test-only-StrongPassword-47',is_staff=True)
        cls.customer.user_permissions.set(Permission.objects.filter(content_type__app_label='cafe').exclude(codename__in=['add_seasonsettings','delete_seasonsettings']))
    def setUp(self):rendered_pages.cache_clear()
    def test_public_pages_and_data(self):
        for page in ['/','/menu.html','/contacts.html']:
            response=self.client.get(page);self.assertEqual(response.status_code,200);self.assertContains(response,'Тёплый угол',html=False)
        data=self.client.get('/menu-data.json').json();self.assertEqual(len(data['items']),8);self.assertTrue(data['serverManaged']);self.assertTrue(data['items'][0]['image'].startswith('/static/assets/'))
    def test_customer_can_edit_menu_but_not_users(self):
        self.assertEqual(self.client.get('/admin/cafe/menuitem/').status_code,302)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get('/admin/cafe/menuitem/').status_code,200)
        self.assertEqual(self.client.get('/admin/auth/user/').status_code,403)
        item=MenuItem.objects.first()
        form={'slug':item.slug,'name':item.name,'category':item.category,'price':299,'portion':item.portion,'description':item.description,'allergens':item.allergens,'default_image':item.default_image,'season':item.season,'position':0,'visible':'on','_save':'Сохранить'}
        response=self.client.post(f'/admin/cafe/menuitem/{item.pk}/change/',form);self.assertEqual(response.status_code,302)
        item.refresh_from_db();self.assertEqual(item.price,299)
        self.assertContains(self.client.get('/menu.html'),'299 ₽');self.assertContains(self.client.get('/'),'299 ₽')
        call_command('import_menu',verbosity=0);item.refresh_from_db();self.assertEqual(item.price,299)
    def test_csrf_and_password_login(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/admin/login/',{'username':'customer','password':'test-only-StrongPassword-47'}).status_code,403)
        self.assertTrue(self.client.login(username='customer',password='test-only-StrongPassword-47'))
        self.assertFalse(self.client.login(username='customer',password='wrong'))
    def test_season_and_hidden_items(self):
        season=SeasonSettings.objects.get();season.season='summer';season.title='Лето в чашке';season.save()
        self.assertNotContains(self.client.get('/menu.html'),'id="seasonal-latte"')
        item=MenuItem.objects.first();item.visible=False;item.save()
        self.assertNotContains(self.client.get('/menu.html'),'id="cappuccino"')
    def test_upload_validation_and_serving(self):
        with tempfile.TemporaryDirectory() as tmp,override_settings(MEDIA_ROOT=Path(tmp)):
            item=MenuItem.objects.first();buf=io.BytesIO();Image.new('RGB',(40,40),'red').save(buf,'PNG')
            item.image=SimpleUploadedFile('my-photo.png',buf.getvalue(),content_type='image/png');item.full_clean();item.save()
            self.assertEqual(self.client.get(item.image.url).status_code,200)
            self.assertEqual(self.client.get('/menu-data.json').json()['items'][0]['image'],item.image.url)
            self.assertContains(self.client.get('/menu.html'),item.image.url)
            item.image=SimpleUploadedFile('bad.jpg',b'not an image',content_type='image/jpeg')
            with self.assertRaises(ValidationError):item.full_clean()
            self.assertEqual(self.client.get('/media/../db.sqlite3').status_code,404)
