import io,json,re,sys,zipfile,mimetypes
from functools import lru_cache
from pathlib import Path
from django.conf import settings
from django.http import HttpResponse,JsonResponse,FileResponse,Http404
from django.views.decorators.http import require_GET
from .models import MenuItem,SeasonSettings

def menu_data():
    season=SeasonSettings.objects.filter(pk=1).first()
    items=[]
    for item in MenuItem.objects.all():
        items.append({'id':item.slug,'name':item.name,'category':item.category,'price':item.price,'portion':item.portion,'description':item.description,'allergens':item.allergens,'badge':item.badge,'label':item.label,'image':item.image.url if item.image else '/static/'+item.default_image,'visible':item.visible,'season':item.season})
    return {'version':1,'serverManaged':True,'season':season.season if season else 'winter','seasonTitle':season.title if season else 'Сезонные предложения','seasonDescription':season.description if season else 'Выберите свой любимый напиток.','items':items}
@require_GET
def data_view(request):return JsonResponse(menu_data(),json_dumps_params={'ensure_ascii':False})
@lru_cache(maxsize=6)
def rendered_pages(serialized):
    sys.path.insert(0,str(settings.PROJECT_DIR))
    from admin_server import export
    with zipfile.ZipFile(io.BytesIO(export(json.loads(serialized)))) as archive:
        return {name:archive.read(name).decode() for name in ('index.html','menu.html','contacts.html')}
@require_GET
def page(request,name='index.html'):
    from django.utils import timezone
    data=menu_data();data['_renderMonth']=timezone.localdate().month
    text=rendered_pages(json.dumps(data,ensure_ascii=False,sort_keys=True))[name]
    text=text.replace('src="assets/','src="/static/assets/').replace('href="assets/','href="/static/assets/')
    for asset in ['style.css','script.js','menu-render.js']:text=text.replace('"'+asset+'"','"/static/'+asset+'"')
    # Для production-версии нет браузерных черновиков: только общие данные сервера.
    canonical=request.build_absolute_uri('/' if name=='index.html' else '/'+name)
    text=re.sub(r'<link rel="canonical"[^>]+>',f'<link rel="canonical" href="{canonical}">',text)
    text=re.sub(r'<meta property="og:url"[^>]+>',f'<meta property="og:url" content="{canonical}">',text)
    text=re.sub(r'<meta property="og:image"[^>]+>',f'<meta property="og:image" content="{request.build_absolute_uri("/static/assets/coffee-shop.webp")}">',text)
    return HttpResponse(text)
@require_GET
def media(request,path):
    if not re.fullmatch(r'menu/[a-f0-9]{32}\.(jpg|jpeg|png|webp)',path):raise Http404
    file=settings.MEDIA_ROOT/path
    if not file.is_file():raise Http404
    response=FileResponse(file.open('rb'),content_type=mimetypes.guess_type(file.name)[0]);response['X-Content-Type-Options']='nosniff';return response
