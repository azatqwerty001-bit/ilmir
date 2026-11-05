from django.contrib import admin
from django.urls import path
from cafe import views
urlpatterns=[path('',views.page),path('index.html',views.page),path('menu.html',views.page,{'name':'menu.html'}),path('contacts.html',views.page,{'name':'contacts.html'}),path('menu-data.json',views.data_view),path('admin/',admin.site.urls),path('media/<path:path>',views.media)]
