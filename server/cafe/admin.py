from django.contrib import admin
from .models import MenuItem,SeasonSettings
admin.site.site_header='Тёплый угол — управление'
admin.site.site_title='Админка кофейни'
admin.site.index_title='Меню и сезонные предложения'
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display=['name','price','category','season','visible','position']
    list_editable=['price','visible','position']
    list_filter=['category','season','visible']
    search_fields=['name','description']
    prepopulated_fields={'slug':('name',)}
    fields=['name','slug','category','price','portion','description','allergens','badge','label','default_image','image','season','visible','position']
@admin.register(SeasonSettings)
class SeasonAdmin(admin.ModelAdmin):
    fields=['season','title','description']
    def has_add_permission(self,request):return not SeasonSettings.objects.exists() and super().has_add_permission(request)
    def has_delete_permission(self,request,obj=None):return False

from .forms import LimitedAdminAuthenticationForm
admin.site.login_form=LimitedAdminAuthenticationForm
