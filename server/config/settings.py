import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
BASE_DIR=Path(__file__).resolve().parents[1]
PROJECT_DIR=BASE_DIR.parent
DEBUG=os.environ.get('DJANGO_DEBUG')=='1'
SECRET_KEY=os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG: SECRET_KEY='local-development-only-key-not-for-hosting'
    else: raise ImproperlyConfigured('Set DJANGO_SECRET_KEY before starting the hosted site')
ALLOWED_HOSTS=[h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1').split(',') if h.strip()]
CSRF_TRUSTED_ORIGINS=[v.strip() for v in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS','').split(',') if v.strip()]
INSTALLED_APPS=['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','cafe']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
DATA_DIR=Path(os.environ.get('CAFE_DATA_DIR',str(PROJECT_DIR.parent/'.ilmir-production')))
DATA_DIR.mkdir(parents=True,exist_ok=True)
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':DATA_DIR/'db.sqlite3','OPTIONS':{'timeout':30}}}
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE='ru-ru'
TIME_ZONE='Europe/Moscow'
USE_I18N=True
USE_TZ=True
STATIC_URL='/static/'
STATIC_ROOT=Path(os.environ.get('DJANGO_STATIC_ROOT',str(BASE_DIR/'staticfiles')))
STATICFILES_DIRS=[BASE_DIR/'public_static'] if (BASE_DIR/'public_static').exists() else []
STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
MEDIA_ROOT=DATA_DIR/'uploads'
MEDIA_URL='/media/'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE='Lax'
SESSION_COOKIE_AGE=28800
SESSION_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
SECURE_SSL_REDIRECT=not DEBUG
SECURE_HSTS_SECONDS=3600 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS='DENY'
DATA_UPLOAD_MAX_MEMORY_SIZE=7*1024*1024
FILE_UPLOAD_MAX_MEMORY_SIZE=5*1024*1024
# Set only behind a trusted proxy that overwrites this header.
if os.environ.get('DJANGO_TRUST_PROXY')=='1':SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
