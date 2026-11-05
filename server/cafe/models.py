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

class BotCart(models.Model):
    bot_key=models.CharField(max_length=16)
    chat_id=models.BigIntegerField()
    items=models.JSONField(default=dict)
    review=models.JSONField(default=dict)
    updated=models.DateTimeField(auto_now=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['bot_key','chat_id'],name='unique_bot_cart')]

class BotEvent(models.Model):
    bot_key=models.CharField(max_length=16)
    update_id=models.BigIntegerField()
    reply=models.JSONField(default=dict)
    created=models.DateTimeField(auto_now_add=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['bot_key','update_id'],name='unique_bot_update')]

ORDER_STATUSES=[('new','Новый'),('accepted','Принят'),('ready','Готов'),('issued','Выдан'),('cancelled','Отменён')]
ORDER_TRANSITIONS={'new':{'accepted','cancelled'},'accepted':{'ready','cancelled'},'ready':{'issued','cancelled'},'issued':set(),'cancelled':set()}
class Order(models.Model):
    bot_key=models.CharField(max_length=16)
    chat_id=models.BigIntegerField('Telegram ID гостя')
    confirmation=models.CharField(max_length=64,unique=True)
    lines=models.JSONField('Состав заказа')
    total=models.PositiveIntegerField('Сумма, ₽')
    pickup=models.CharField('Самовывоз',max_length=100)
    status=models.CharField('Статус',choices=ORDER_STATUSES,max_length=12,default='new')
    created=models.DateTimeField('Создан',auto_now_add=True)
    updated=models.DateTimeField(auto_now=True)
    class Meta:ordering=['-created'];verbose_name='учебный заказ';verbose_name_plural='Заказы'
    def __str__(self):return f'Заказ №{self.pk}'
    def clean(self):
        super().clean()
        if self.pk:
            previous=Order.objects.get(pk=self.pk).status
            if self.status!=previous and self.status not in ORDER_TRANSITIONS.get(previous,set()):raise ValidationError({'status':'Недопустимый переход. Новый → Принят → Готов → Выдан; до выдачи можно отменить.'})
    def save(self,*args,**kwargs):
        from django.db import transaction
        with transaction.atomic():
            old=Order.objects.select_for_update().filter(pk=self.pk).first() if self.pk else None
            if old and self.status!=old.status and self.status not in ORDER_TRANSITIONS.get(old.status,set()):raise ValidationError('Недопустимый переход статуса')
            super().save(*args,**kwargs)
            if old and old.status!=self.status:OrderNotice.objects.create(order=self,status=self.status)

class OrderNotice(models.Model):
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name='notices')
    status=models.CharField(max_length=12,choices=ORDER_STATUSES)
    created=models.DateTimeField(auto_now_add=True)
    sent_at=models.DateTimeField('Отправлено',null=True,blank=True)
    attempts=models.PositiveIntegerField('Попыток',default=0)
    retry_at=models.DateTimeField(null=True,blank=True)
    error=models.CharField('Ошибка доставки',max_length=100,blank=True)
    permanent_failure=models.BooleanField('Доставка невозможна',default=False)
    class Meta:ordering=['created'];verbose_name='уведомление';verbose_name_plural='Уведомления'
