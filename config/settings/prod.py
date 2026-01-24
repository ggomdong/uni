import environ
from .base import *

ALLOWED_HOSTS = ['52.78.193.52', '.wsnuni.co.kr']
STATIC_ROOT = BASE_DIR / 'static/'
STATICFILES_DIRS = []
DEBUG = False

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

INITIAL_PASSWORD_SUFFIX = env('INITIAL_PASSWORD_SUFFIX', default=None)
if not INITIAL_PASSWORD_SUFFIX:
    raise ImproperlyConfigured("INITIAL_PASSWORD_SUFFIX is not set in .env")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': '3306',
    }
}