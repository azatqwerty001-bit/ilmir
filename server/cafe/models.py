import uuid
from pathlib import Path
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator,MinValueValidator,FileExtensionValidator

def image_name(instance,filename):return 'menu/'+uuid.uuid4().hex+Path(filename).suffix.lower()

class SeasonSettings(models.Model):
    season=models.CharField('Сезон',max_length=10,choices=[('winter','Осень / зима'),('summer','Лето'),('auto','Автоматически')],default='winter')
    title=models.CharField('Заголовок баннера',max_length=200,default='Согреться — тоже план.')
    description=models.TextField('Описание баннера',max_length=1000,default='Пряный латте и чай с имбирём.')
    updated=models.DateTimeField(auto_now=True)
    class Meta:verbose_name='настройки сезона';verbose_name_plural='Настройки сезона'
    def __str__(self):return 'Сезонное предложение'
    def save(self,*args,**kwargs):
        self.pk=1
        return super().save(*args,**kwargs)

class MenuItem(models.Model):
    slug=models.SlugField('Уникальный код',unique=True,max_length=60)
    name=models.CharField('Название',max_length=200)
    category=models.CharField('Категория',max_length=10,choices=[('coffee','Кофе'),('food','Выпечка и завтраки'),('seasonal','Сезонное')])
    price=models.PositiveIntegerField('Цена, ₽',validators=[MinValueValidator(1),MaxValueValidator(100000)])
    portion=models.CharField('Порция',max_length=80)
    description=models.TextField('Состав',max_length=2000)
    allergens=models.CharField('Аллергены',max_length=500)
    badge=models.CharField('Пометка',max_length=200,blank=True)
    label=models.CharField('Надпись на фото',max_length=100,blank=True)
    default_image=models.CharField('Фото из галереи',max_length=120,choices=[(f'assets/{n}.webp',n) for n in ['cappuccino','latte','croissant','filter-coffee','toast','cake','seasonal-latte','seasonal-tea','coffee-detail']],default='assets/cappuccino.webp')
    image=models.ImageField('Своя фотография (до 5 МБ)',upload_to=image_name,blank=True,validators=[FileExtensionValidator(['jpg','jpeg','png','webp'])])
    visible=models.BooleanField('Показывать на сайте',default=True)
    season=models.CharField('Сезон позиции',max_length=10,choices=[('all','Любой'),('winter','Осень / зима'),('summer','Лето')],default='all')
    position=models.PositiveIntegerField('Порядок',default=0)
    updated=models.DateTimeField(auto_now=True)
    class Meta:ordering=['position','id'];verbose_name='позиция меню';verbose_name_plural='Меню'
    def __str__(self):return self.name
    def clean(self):
        super().clean()
        if self.image:
            if self.image.size>5*1024*1024:raise ValidationError({'image':'Максимальный размер — 5 МБ'})
            from PIL import Image
            try:
                self.image.open()
                with Image.open(self.image) as img:
                    if img.width*img.height>25000000:raise ValueError('Слишком большое изображение')
                    img.verify()
                self.image.seek(0)
            except Exception as exc:raise ValidationError({'image':'Загрузите корректное JPG, PNG или WebP до 25 мегапикселей'}) from exc
