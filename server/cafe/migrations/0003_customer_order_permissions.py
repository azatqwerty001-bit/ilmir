from django.db import migrations

def upgrade(apps,schema_editor):
    Group=apps.get_model('auth','Group');Permission=apps.get_model('auth','Permission');ContentType=apps.get_model('contenttypes','ContentType')
    group,_=Group.objects.get_or_create(name='Заказчик кофейни')
    permissions=[]
    for model,actions in [('menuitem',['add','change','delete','view']),('seasonsettings',['change','view']),('order',['view','change']),('ordernotice',['view'])]:
        ct,_=ContentType.objects.get_or_create(app_label='cafe',model=model)
        for action in actions:
            permission,_=Permission.objects.get_or_create(content_type=ct,codename=action+'_'+model,defaults={'name':action+' '+model})
            permissions.append(permission)
    group.permissions.set(permissions)
class Migration(migrations.Migration):
    dependencies=[('cafe','0002_order_botcart_botevent_ordernotice')]
    operations=[migrations.RunPython(upgrade,migrations.RunPython.noop)]
