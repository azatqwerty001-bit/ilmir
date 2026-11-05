from django.contrib.auth.models import Group,Permission

def customer_group():
    group,_=Group.objects.get_or_create(name='Заказчик кофейни')
    codes=['add_menuitem','change_menuitem','delete_menuitem','view_menuitem','change_seasonsettings','view_seasonsettings','view_order','change_order','view_ordernotice']
    group.permissions.set(Permission.objects.filter(content_type__app_label='cafe',codename__in=codes))
    return group
